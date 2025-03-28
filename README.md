# Chatbot Summit 20025

## Setup

### Pre requesities
* a free Rasa Pro [Developer Edition license](https://rasa.com/docs/rasa-pro/developer-edition)
* an API key for Speech Services
  - Deepgram for ASR
  - Cartesia (TTS) or Azure (TTS)



### Install

* Install Rasa Pro 3.12 alpha version 
```
uv pip install "rasa-pro==3.12.0"
```

* Set environment variables

```
export RASA_PRO_LICENSE="LICENSE_KEY"
export DEEPGRAM_API_KEY="LICENSE_KEY"
export CARTESIA_API_KEY="LICENSE_KEY"
export AZURE_SPEECH_API_KEY="LICENSE_KEY" #if you are using Azure speech services
```


### Configuration

Integrate the channel connector for voice native
```yaml
browser_audio:
  server_url: localhost
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
rasa inspect --voice

```

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

