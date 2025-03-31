import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
import base64
import time 

import structlog
import websockets
import websockets.exceptions
from websockets.legacy.client import WebSocketClientProtocol

from rasa.core.channels.voice_stream.asr.asr_engine import ASREngine, ASREngineConfig
from rasa.core.channels.voice_stream.asr.asr_event import (
    ASREvent,
    NewTranscript,
    UserIsSpeaking,
)
from rasa.core.channels.voice_stream.audio_bytes import HERTZ, RasaAudioBytes

logger = structlog.get_logger(__name__)

SPEECHMATICS_API_KEY_ENV_VAR = "SPEECHMATICS_API_KEY"

@dataclass
class SpeechmaticsASRConfig(ASREngineConfig):
    endpoint: Optional[str] = None
    language: Optional[str] = None
    operating_point: Optional[str] = None


class SpeechmaticsASR(ASREngine[SpeechmaticsASRConfig]):
    required_env_vars = (SPEECHMATICS_API_KEY_ENV_VAR,)

    def __init__(self, config: Optional[SpeechmaticsASRConfig] = None):
        super().__init__(config)
        self.accumulated_transcript = ""
        self.connection_message_sent = False
        # Buffer to accumulate audio data
        self.audio_buffer = bytearray()
        # Size of chunks to send to Speechmatics (in bytes)
        self.chunk_size = 4096  # 4KB chunks
        self.speech_end_time = None

    async def open_websocket_connection(self) -> WebSocketClientProtocol:
        """Connect to the Speechmatics ASR system."""
        speechmatics_api_key = os.environ[SPEECHMATICS_API_KEY_ENV_VAR]
        extra_headers = {"Authorization": f"Bearer {speechmatics_api_key}"}
        try:
            # Important: Use proper subprotocol for Speechmatics
            websocket = await websockets.connect(  # type: ignore
                self._get_api_url(),
                extra_headers=extra_headers,
                subprotocols=["json"],  # Critical: Specify 'json' subprotocol
            )
            # Send the initial configuration message
            await self._send_connection_message(websocket)
            return websocket
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 401:
                error_msg = "Please make sure your Speechmatics API key is correct."
            else:
                error_msg = f"Connection to Speechmatics failed with status {e.status_code}."
            logger.error(
                "speechmatics.connection.failed",
                status_code=e.status_code,
                error=error_msg,
            )
            raise

    async def _send_connection_message(self, websocket: WebSocketClientProtocol) -> None:
        """Send initial configuration message to Speechmatics."""
        connection_message = {
            "message": "StartRecognition",
            "audio_format": {
                "type": "raw",
                "encoding": "mulaw",  # Use standard PCM format
                "sample_rate": HERTZ
            },
            "transcription_config": {
                "language": self.config.language,
                "enable_partials": False,
                "max_delay": 2.0,
            }
        }
            
        if self.config.operating_point:
            connection_message["transcription_config"]["operating_point"] = self.config.operating_point
        
        # Send the configuration message as JSON text
        json_msg = json.dumps(connection_message)
        logger.debug("speechmatics.connection_message", message=json_msg)
        await websocket.send(json_msg)
        self.connection_message_sent = True
        logger.info("speechmatics.connection_message.sent")

    def _get_api_url(self) -> str:
        """Get the API URL with the configured endpoint."""
        return f"wss://{self.config.endpoint}/v2"

    async def signal_audio_done(self) -> None:
        """Signal to the Speechmatics API that you are done sending data."""
        if self.asr_socket is None:
            raise AttributeError("Websocket not connected.")
        
        
        # First, send any remaining audio in the buffer
        await self._flush_audio_buffer()
        
        # Then send EndOfStream message as JSON
        end_message = json.dumps({"message": "EndOfStream"})
        await self.asr_socket.send(end_message)
        logger.info("speechmatics.end_of_stream.sent")

    def rasa_audio_bytes_to_engine_bytes(self, chunk: RasaAudioBytes) -> bytes:
        """Convert RasaAudioBytes to bytes usable by Speechmatics."""
        return chunk

    async def process_audio(self, chunk: RasaAudioBytes) -> None:
        """Process audio chunk by adding to buffer and sending when full."""
        if self.asr_socket is None:
            raise AttributeError("Websocket not connected.")
        
        # Convert to the format needed by Speechmatics
        converted_chunk = self.rasa_audio_bytes_to_engine_bytes(chunk)
        
        # Add to our buffer
        self.audio_buffer.extend(converted_chunk)
        
        # If buffer is larger than chunk size, send chunks
        await self._flush_audio_buffer()

    async def _flush_audio_buffer(self) -> None:
        """Send accumulated audio data in appropriate sized chunks."""
        if not self.audio_buffer:
            return
            
        if self.asr_socket is None:
            raise AttributeError("Websocket not connected.")
        
        try:
            # Create AddAudio message with base64 encoded audio
            audio_base64 = base64.b64encode(self.audio_buffer).decode('utf-8')            
            # Convert to JSON and send
            await self.asr_socket.send(audio_base64)
            
            # Clear buffer after sending
            self.audio_buffer = bytearray()
        except Exception as e:
            logger.error("speechmatics.send_audio.failed", error=str(e))
            raise

    def engine_event_to_asr_event(self, e: Any) -> Optional[ASREvent]:
        """Translate a Speechmatics event to a common ASREvent."""
        try:
            data = json.loads(e) if isinstance(e, str) else e
            message_type = data.get("message")
            if message_type == "AudioAdded":
                self.speech_end_time = time.time()
                logger.info("speechmatics.audio_received", timestamp=self.speech_end_time)
            # Only process AddTranscript messages
            if message_type == "AddTranscript":
                # Check if there are any results
                results = data.get("results", [])
                metadata = data.get("metadata", {})
                transcript = metadata.get("transcript", "").strip()

                # Look for end of sentence marker
                is_end_of_sentence = False
                for result in results:
                    if result.get("type") == "punctuation" and result.get("is_eos") is True:
                        is_end_of_sentence = True
                        break
                    
                # Option 1: Return final transcript when we see end of sentence punctuation
                if is_end_of_sentence and self.accumulated_transcript:
                    # Add the current transcript to the accumulated one
                    full_transcript = self.concatenate_transcripts(
                        self.accumulated_transcript, transcript
                    )
                    self.accumulated_transcript = ""
                    now = time.time()
                    latency = None

                    if self.speech_end_time:
                        latency = now - self.speech_end_time
                        logger.info(
                            "speechmatics.transcript.sentence_complete", 
                            transcript=full_transcript,
                            latency_from_speech_end=f"{latency:.3f}s"
                        )
                    
                    return NewTranscript(full_transcript)

                # Option 2: Process based on silence detection (empty transcript after non-empty)
                elif not transcript and self.accumulated_transcript:
                    # No new content in this segment but we have accumulated transcript
                    # This could indicate a pause in speech

                    # Check if this is a substantial pause (check time gap)
                    start_time = metadata.get("start_time", 0)
                    end_time = metadata.get("end_time", 0)
                    silence_duration = end_time - start_time

                    # If silence is long enough (e.g., > 0.7 seconds), treat as end of utterance
                    if silence_duration > 0.7:
                        full_transcript = self.accumulated_transcript
                        self.accumulated_transcript = ""
                        latency = None
                        if self.speech_end_time:
                            latency = now - self.speech_end_time
                            logger.info(
                                "speechmatics.transcript.sentence_complete", 
                                transcript=full_transcript,
                                latency_from_speech_end=f"{latency:.3f}s"
                            )
                        return NewTranscript(full_transcript)

                # Accumulate transcript if there's content
                if transcript:
                    self.accumulated_transcript = self.concatenate_transcripts(
                        self.accumulated_transcript, transcript
                    )
                    # Signal that user is speaking
                    return UserIsSpeaking()

        except Exception as e:
            logger.error("speechmatics.parse_error", error=str(e))

        return None

    @staticmethod
    def get_default_config() -> SpeechmaticsASRConfig:
        return SpeechmaticsASRConfig(
            endpoint="eu2.rt.speechmatics.com/",
            language="en",
            operating_point="enhanced",
        )

    @classmethod
    def from_config_dict(cls, config: Dict) -> "SpeechmaticsASR":
        return SpeechmaticsASR(SpeechmaticsASRConfig.from_dict(config))

    @staticmethod
    def concatenate_transcripts(t1: str, t2: str) -> str:
        """Concatenate two transcripts making sure there is a space between them."""
        return (t1.strip() + " " + t2.strip()).strip()

    def has_required_env_vars(self) -> bool:
        """Check if all required environment variables are set."""
        speechmatics_key = os.environ.get(SPEECHMATICS_API_KEY_ENV_VAR)
        if not speechmatics_key:
            logger.error(
                "speechmatics.missing_api_key",
                error=f"{SPEECHMATICS_API_KEY_ENV_VAR} environment variable is missing"
            )
            return False
        return True