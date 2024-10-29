# CALM SUMMIT 2024 - Masterclass

## Setup

### Pre requesities
* a free Rasa Pro [Developer Edition license](https://rasa.com/docs/rasa-pro/developer-edition)
* an API key for OpenAI or another [LLM provider](https://rasa.com/docs/rasa-pro/concepts/components/llm-configuration)
* an API key for Speech Services
  - Deepgram for ASR (only supported for alpha)
  - Cartesia (TTS) or Azure (TTS)
* Twilio account and a phone number (Optional for IVR). 


### Install

* Install Rasa Pro 3.11 alpha version 
```
uv pip install "rasa-pro==3.11.0a3" --prerelease=allow
```

* Set environment variables

```
export RASA_PRO_LICENSE="LICENSE_KEY"
export OPENAI_API_KEY="LICNESE_KEY" #optional if you using another provider
export DEEPGRAM_API_KEY="LICENSE_KEY" # for alpha, we only support deepgram
export CARTESIA_API_KEY="LICENSE_KEY"
```


### Configuration

Integrate the channel connector for voice native
```yaml
twilio_media_streams:
  server_url: 8956-2a02-1811-2d87-7800-288a-12d7-22f-edb5.ngrok-free.app
  asr:
    name: deepgram #export DEEPGRAM_API_KEY
  tts:
    name: cartesia #export CARTESIA_API_KEY
```


### Train
```
rasa train
```

### Test

```
rasa run --inspect

```

Open inspector in [read only mode](http://0.0.0.0:5005/webhooks/twilio_media_streams/inspect.html)

Call your bot using Twilio phone number and start talking

Here's an example conversation

## Chat: Happy Path

**User**: I lost my wallet.

**Bot**: I am sorry this happened to you. First things first, we need to secure your accounts. Would you like me to lock all your cards temporarily while we figure things out?

**User**: Yes, let's go ahead and do that.

**Bot**: Understood. Your cards are now temporarily blocked to prevent any unauthorized transactions.

**Bot**: Would you like me to issue replacement cards?

**User**: Yes, I am not getting my wallet back.

**Bot**: I just need to make sure I have your address correct. Is this right?

**Bot**: 1 Embarcadero Center, San Francisco, CA

**User**: Yes, that's correct.

**Bot**: Great. I will send those cards there. You’ll receive them within 3 to 5 business days.

**Bot**: Is there anything else I can help you with?



### Local Testing

Integrate the local channel connector
```
browser_audio:
  server_url: localhost
  asr:
    name: deepgram #export DEEPGRAM_API_KEY
    endpointing: 300
  tts:
    name: cartesia

```

```
rasa inspect --voice
```

Talk to the inspector with voice