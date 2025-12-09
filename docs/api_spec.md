# Resemble AI V2 API Documentation

This document provides comprehensive API documentation for all V2 endpoints in the Resemble AI platform.

## Table of Contents

- [Projects](#projects)
- [Clips](#clips)
- [Recordings](#recordings)
- [Voices](#voices)
- [Voice Settings Presets](#voice-settings-presets)
- [Detect (Deepfake Detection)](#detect-deepfake-detection)
- [Watermark](#watermark)
- [Intelligence](#audio-intelligence)
- [Speech-to-Text](#speech-to-text)
- [Identity (Speaker Identification)](#identity-speaker-identification)
- [Audio Edit](#audio-edit)
- [Audio Enhancements](#audio-enhancements)
- [Voice Design](#voice-design)

---

## Projects

Projects are containers for organizing your audio clips and synthesis work.

### List Projects

**Endpoint:** `GET /api/v2/projects`

**Description:** Retrieve a paginated list of all projects for the authenticated user.

**Request Parameters:**
- `page` (query, integer, optional): Page number for pagination
- `per_page` (query, integer, optional): Number of items per page

**Response:**
```json
{
  "success": true,
  "page": 1,
  "total_results": 10,
  "page_count": 1,
  "items": [
    {
      "uuid": "string",
      "name": "string",
      "description": "string",
      "is_collaborative": boolean,
      "is_archived": boolean,
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
}
```

### Get Project

**Endpoint:** `GET /api/v2/projects/:uuid`

**Description:** Retrieve details of a specific project.

**URL Parameters:**
- `uuid` (string, required): Project UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "description": "string",
    "is_collaborative": boolean,
    "is_archived": boolean,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Create Project

**Endpoint:** `POST /api/v2/projects`

**Description:** Create a new project.

**Request Body:**
- `name` (string, required): Project name (max 256 characters)
- `description` (string, optional): Project description (max 1024 characters)
- `is_collaborative` (boolean, optional): Whether project is collaborative
- `is_archived` (boolean, optional): Whether project is archived

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "description": "string",
    "is_collaborative": boolean,
    "is_archived": boolean,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Update Project

**Endpoint:** `PATCH /api/v2/projects/:uuid` or `PUT /api/v2/projects/:uuid`

**Description:** Update an existing project.

**URL Parameters:**
- `uuid` (string, required): Project UUID

**Request Body:**
- `name` (string, optional): Project name (max 256 characters)
- `description` (string, optional): Project description (max 1024 characters)
- `is_collaborative` (boolean, optional): Whether project is collaborative
- `is_archived` (boolean, optional): Whether project is archived

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "description": "string",
    "is_collaborative": boolean,
    "is_archived": boolean,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Delete Project

**Endpoint:** `DELETE /api/v2/projects/:uuid`

**Description:** Delete a project.

**URL Parameters:**
- `uuid` (string, required): Project UUID

**Response:**
```json
{
  "success": true
}
```

---

## Clips

Clips are text-to-speech synthesis jobs within a project.

### List Clips

**Endpoint:** `GET /api/v2/projects/:project_uuid/clips`

**Description:** Retrieve a paginated list of clips in a project.

**URL Parameters:**
- `project_uuid` (string, required): Project UUID

**Query Parameters:**
- `q` (string, optional): Search query to filter clips by title
- `page` (query, integer, optional): Page number for pagination
- `per_page` (query, integer, optional): Number of items per page

**Response:**
```json
{
  "success": true,
  "page": 1,
  "total_results": 10,
  "page_count": 1,
  "items": [
    {
      "uuid": "string",
      "title": "string",
      "body": "string",
      "voice_uuid": "string",
      "voice_name": "string",
      "is_archived": boolean,
      "audio_src": "string (URL)",
      "character_count": integer,
      "duration": number,
      "last_generated_at": "datetime",
      "timestamps": object,
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
}
```

### Get Clip

**Endpoint:** `GET /api/v2/projects/:project_uuid/clips/:uuid`

**Description:** Retrieve details of a specific clip.

**URL Parameters:**
- `project_uuid` (string, required): Project UUID
- `uuid` (string, required): Clip UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "title": "string",
    "body": "string",
    "voice_uuid": "string",
    "voice_name": "string",
    "is_archived": boolean,
    "audio_src": "string (URL)",
    "character_count": integer,
    "duration": number,
    "last_generated_at": "datetime",
    "timestamps": object,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Create Clip

**Endpoint:** `POST /api/v2/projects/:project_uuid/clips`

**Description:** Create a new clip and synthesize speech.

**URL Parameters:**
- `project_uuid` (string, required): Project UUID

**Request Body:**
- `title` (string, optional): Clip title (max 256 characters)
- `body` (string, required): Text to synthesize (subject to plan character limits)
- `voice_uuid` (string, required): UUID of voice to use for synthesis
- `is_archived` (boolean, optional): Whether clip is archived
- `callback_uri` (string, optional): HTTPS URL for async callback (enables async mode)
- `sample_rate` (integer, optional): Audio sample rate (8000, 16000, 22050, 24000, 32000, 44100, 48000). Default: 22050
- `precision` (string, optional): Audio precision (PCM_16, PCM_24, PCM_32). Default: PCM_32
- `output_format` (string, optional): Output format (wav, mp3, ogg, flac, etc.). Default: wav
- `suggestions` (boolean, optional): Enable pronunciation suggestions
- `raw` (boolean, optional): Include raw audio data in response

**Response (Sync):**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "title": "string",
    "body": "string",
    "voice_uuid": "string",
    "audio_src": "string (URL)",
    "raw_audio": "base64 (if raw=true)",
    "timestamps": object,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Response (Async with callback_uri):**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "title": "string",
    "body": "string",
    "voice_uuid": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- Sync synthesis only works for non-enhanced voices and for clips under 2000 characters with callback_uri
- Enhanced voices require async synthesis (provide callback_uri)
- AWS and Google voices always synthesize asynchronously
- Character limits depend on your plan's characters_per_clip setting
- Maximum 4000 characters per segment

### Update Clip

**Endpoint:** `PATCH /api/v2/projects/:project_uuid/clips/:uuid` or `PUT /api/v2/projects/:project_uuid/clips/:uuid`

**Description:** Update a clip and re-synthesize speech. Only async updates are supported.

**URL Parameters:**
- `project_uuid` (string, required): Project UUID
- `uuid` (string, required): Clip UUID

**Request Body:**
- `title` (string, optional): Clip title (max 256 characters)
- `body` (string, optional): Text to synthesize
- `voice_uuid` (string, optional): UUID of voice to use
- `is_archived` (boolean, optional): Whether clip is archived
- `callback_uri` (string, required): HTTPS URL for async callback
- `sample_rate` (integer, optional): Audio sample rate
- `precision` (string, optional): Audio precision
- `output_format` (string, optional): Output format

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "title": "string",
    "body": "string",
    "voice_uuid": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Delete Clip

**Endpoint:** `DELETE /api/v2/projects/:project_uuid/clips/:uuid`

**Description:** Delete a clip and all its segments.

**URL Parameters:**
- `project_uuid` (string, required): Project UUID
- `uuid` (string, required): Clip UUID

**Response:**
```json
{
  "success": true
}
```

---

## Recordings

Recordings are audio samples used to train custom voices.

### List Recordings

**Endpoint:** `GET /api/v2/voices/:voice_uuid/recordings`

**Description:** Retrieve a paginated list of recordings for a voice.

**URL Parameters:**
- `voice_uuid` (string, required): Voice UUID

**Query Parameters:**
- `page` (query, integer, optional): Page number for pagination
- `per_page` (query, integer, optional): Number of items per page

**Response:**
```json
{
  "success": true,
  "page": 1,
  "total_results": 10,
  "page_count": 1,
  "items": [
    {
      "uuid": "string",
      "name": "string",
      "text": "string",
      "emotion": "string",
      "fill": boolean,
      "is_active": boolean,
      "audio_src": "string (URL)",
      "metrics": {
        "signal_to_noise_ratio": number,
        "loudness_grade": string,
        "resemble_sample_score": number
      },
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
}
```

### Get Recording

**Endpoint:** `GET /api/v2/voices/:voice_uuid/recordings/:uuid`

**Description:** Retrieve details of a specific recording.

**URL Parameters:**
- `voice_uuid` (string, required): Voice UUID
- `uuid` (string, required): Recording UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "text": "string",
    "emotion": "string",
    "fill": boolean,
    "is_active": boolean,
    "audio_src": "string (URL)",
    "metrics": {
      "signal_to_noise_ratio": number,
      "loudness_grade": string,
      "resemble_sample_score": number
    },
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Create Recording

**Endpoint:** `POST /api/v2/voices/:voice_uuid/recordings`

**Description:** Upload a new recording for a voice. Must be multipart/form-data.

**URL Parameters:**
- `voice_uuid` (string, required): Voice UUID

**Request Body (multipart/form-data):**
- `file` (file, required): Audio file (must be between configured duration bounds)
- `name` (string, required): Recording name (max 256 characters, must be unique for this voice)
- `text` (string, required): Transcript of the audio (max 1024 characters)
- `emotion` (string, optional): Emotion label (max 64 characters)
- `is_active` (boolean, optional): Whether recording is active for training. Default: true
- `fill` (boolean, optional): Whether to use for fill/speech-to-speech

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "text": "string",
    "emotion": "string",
    "fill": boolean,
    "is_active": boolean,
    "audio_src": "string (URL)",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- Audio file must not be silent
- Audio duration must be within configured bounds (typically 1-60 seconds)
- Cannot upload recordings to pre-built or marketplace voices

### Update Recording

**Endpoint:** `PATCH /api/v2/voices/:voice_uuid/recordings/:uuid` or `PUT /api/v2/voices/:voice_uuid/recordings/:uuid`

**Description:** Update recording metadata.

**URL Parameters:**
- `voice_uuid` (string, required): Voice UUID
- `uuid` (string, required): Recording UUID

**Request Body:**
- `name` (string, optional): Recording name (max 256 characters)
- `text` (string, optional): Transcript (max 1024 characters)
- `emotion` (string, optional): Emotion label (max 64 characters)
- `is_active` (boolean, optional): Whether recording is active for training
- `fill` (boolean, optional): Whether to use for fill/speech-to-speech

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "text": "string",
    "emotion": "string",
    "fill": boolean,
    "is_active": boolean,
    "audio_src": "string (URL)",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- Cannot activate recordings marked as outliers

### Delete Recording

**Endpoint:** `DELETE /api/v2/voices/:voice_uuid/recordings/:uuid`

**Description:** Delete a recording.

**URL Parameters:**
- `voice_uuid` (string, required): Voice UUID
- `uuid` (string, required): Recording UUID

**Response:**
```json
{
  "success": true
}
```

### Get All Recordings (Internal)

**Endpoint:** `GET /api/v2/voices/:voice_uuid/recordings/all`

**Description:** Internal endpoint to retrieve all recordings for a voice (requires internal authentication).

**URL Parameters:**
- `voice_uuid` (string, required): Voice UUID

**Response:**
```json
[
  {
    "uuid": "string",
    "name": "string",
    "text": "string",
    "emotion": "string",
    "fill": boolean,
    "is_active": boolean,
    "audio_src": "string (URL)",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

---

## Voices

Voices are the core AI models used for speech synthesis.

### List Voices

**Endpoint:** `GET /api/v2/voices`

**Description:** Retrieve a paginated list of voices accessible to the user.

**Query Parameters:**
- `page` (query, integer, optional): Page number
- `per_page` (query, integer, optional): Items per page
- `pre_built_resemble_voice` (boolean, optional): Filter by pre-built voices
- `age` (string, optional): Filter by age (comma-separated values)
- `gender` (string, optional): Filter by gender (comma-separated values)
- `accents` (string, optional): Filter by accents (comma-separated values)
- `use_case` (string, optional): Filter by use case (comma-separated values)
- `tone_of_voice` (string, optional): Filter by tone (comma-separated values)
- `advanced` (boolean, optional): Include advanced model information
- `sample_url` (boolean, optional): Include sample audio URLs
- `filters` (boolean, optional): Include filter metadata
- `voice_selector` (boolean, optional): Format for voice selector UI

**Response:**
```json
{
  "success": true,
  "page": 1,
  "total_results": 10,
  "page_count": 1,
  "items": [
    {
      "uuid": "string",
      "name": "string",
      "status": "string",
      "voice_status": "string",
      "voice_type": "string (rapid_voice, professional)",
      "default_language": "string",
      "supported_languages": ["string"],
      "dataset_url": "string",
      "callback_uri": "string",
      "source": "string (Custom Voice, Resemble Voice, Resemble Marketplace)",
      "dataset_analysis_failure": boolean,
      "component_status": {
        "text_to_speech": { "status": "string" },
        "fill": { "status": "string" },
        "voice_conversion": { "status": "string" }
      },
      "api_support": {
        "sync_tts": boolean,
        "async_tts": boolean,
        "fill": boolean,
        "sts": boolean
      },
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
}
```

**Optional Fields (when advanced=true):**
```json
{
  "model": {
    "text_to_speech": "string",
    "fill": "string",
    "voice_conversion": "string"
  }
}
```

**Optional Fields (when sample_url=true):**
```json
{
  "sample_url": "string (URL)"
}
```

**Optional Fields (when filters=true):**
```json
{
  "filters": {
    "age": "string",
    "gender": "string",
    "accents": ["string"],
    "useCase": ["string"],
    "toneOfVoice": ["string"]
  }
}
```

### Get Voice

**Endpoint:** `GET /api/v2/voices/:uuid`

**Description:** Retrieve details of a specific voice.

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Query Parameters:**
- `advanced` (boolean, optional): Include advanced model information
- `sample_url` (boolean, optional): Include sample audio URL
- `filters` (boolean, optional): Include filter metadata

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "status": "string",
    "voice_status": "string",
    "voice_type": "string",
    "default_language": "string",
    "supported_languages": ["string"],
    "dataset_url": "string",
    "callback_uri": "string",
    "source": "string",
    "component_status": object,
    "api_support": object,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Create Voice

**Endpoint:** `POST /api/v2/voices`

**Description:** Create a new custom voice. Requires Business or Enterprise plan.

**Request Body:**
- `name` (string, required): Voice name (max 256 characters)
- `voice_type` (string, optional): Voice type (rapid_voice or professional). Default: professional
- `language` (string, optional): Default language code. Default: en-US
- `description` (string, optional): Voice description
- `dataset_url` (string, optional): URL to training dataset (max 30,000 characters)
- `callback_uri` (string, optional): Callback URL for training completion (max 1000 characters)

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "status": "string",
    "voice_type": "string",
    "default_language": "string",
    "description": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- For rapid voices, dataset_url must be a valid audio file
- Dataset files are checked against speaker blacklist
- Voice creation respects plan limits for professional and rapid voices

### Update Voice

**Endpoint:** `PATCH /api/v2/voices/:uuid` or `PUT /api/v2/voices/:uuid`

**Description:** Update voice metadata.

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Request Body:**
- `name` (string, optional): Voice name (max 256 characters)
- `description` (string, optional): Voice description
- `dataset_url` (string, optional): URL to training dataset
- `callback_uri` (string, optional): Callback URL
- `language` (string, optional): Default language code

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "status": "string",
    "voice_type": "string",
    "description": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- Cannot update pre-built or marketplace voices

### Delete Voice

**Endpoint:** `DELETE /api/v2/voices/:uuid`

**Description:** Delete a custom voice from your account.

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Response:**
```json
{
  "success": true,
  "message": "Voice was deleted."
}
```

**Notes:**
- For custom voices: permanently deletes the voice

### Build Voice

**Endpoint:** `POST /api/v2/voices/:uuid/build`

**Description:** Start training a voice. Requires Business or Enterprise plan.

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Request Body:**
- `fill` (boolean, optional): Enable fill/speech-to-speech training. Default: false

**Response:**
```json
{
  "success": true
}
```

**Notes:**
- Professional voices require at least 3 active recordings (configurable)
- Rapid voices require at least 1 recording or custom dataset
- Cannot build pre-built or marketplace voices
- Recordings must meet quality standards (not silent, correct duration)

### Upgrade Voice

**Endpoint:** `POST /api/v2/voices/:uuid/upgrade`

**Description:** Upgrade a voice to the latest model version.

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Response:**
```json
{
  "success": true,
  "message": "Voice upgrade started successfully",
  "voice_id": integer
}
```

**Notes:**
- Voice must be in finished, failed, or locked state
- Automatically detects appropriate template for voice type

### Pin Voice

**Endpoint:** `POST /api/v2/voices/:uuid/pin`

**Description:** Pin a voice for quick access.

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Response:**
```json
{
  "success": true,
  "pinned": true
}
```

### Unpin Voice

**Endpoint:** `DELETE /api/v2/voices/:uuid/pin`

**Description:** Unpin a voice.

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Response:**
```json
{
  "success": true,
  "pinned": false
}
```

### Get Custom Voices

**Endpoint:** `GET /api/v2/voices/custom`

**Description:** Retrieve custom voices for the current user.

**Response:**
```json
[
  {
    "uuid": "string",
    "name": "string",
    "status": "string",
    "created_at": "datetime"
  }
]
```

### Get All Voices

**Endpoint:** `GET /api/v2/voices/all`

**Description:** Retrieve all voices including custom, AI voices, pinned voices, and recent voices with presets.

**Response:**
```json
{
  "custom_voices": [object],
  "ai_voices": [object],
  "pinned_voices": [object],
  "recent_voices": [object],
  "voice_settings_presets": {
    "user_presets": [object],
    "default_presets": [object]
  }
}
```

### Get Voice Model URLs (Internal)

**Endpoint:** `GET /api/v2/voices/:uuid/model_urls`

**Description:** Internal endpoint to retrieve model artifact URLs (requires internal authentication).

**URL Parameters:**
- `uuid` (string, required): Voice UUID

**Query Parameters:**
- `replace_names` (boolean, optional): Replace model names. Default: true

**Response:**
```json
{
  "model_urls": object
}
```

---

## Voice Settings Presets

Voice settings presets allow you to save and reuse voice synthesis configurations.

### List Presets

**Endpoint:** `GET /api/v2/voice_settings_presets`

**Description:** Retrieve all voice settings presets (both custom and default).

**Response:**
```json
{
  "success": true,
  "data": {
    "custom_presets": [
      {
        "uuid": "string",
        "name": "string",
        "settings": {
          "pace": number,
          "temperature": number,
          "pitch": number,
          "useHd": boolean,
          "exaggeration": number,
          "description": "string"
        },
        "is_public": boolean,
        "created_at": "datetime",
        "updated_at": "datetime"
      }
    ],
    "default_presets": [
      {
        "uuid": "string",
        "name": "string",
        "settings": object,
        "is_public": boolean,
        "created_at": "datetime",
        "updated_at": "datetime"
      }
    ]
  }
}
```

### Get Preset

**Endpoint:** `GET /api/v2/voice_settings_presets/:uuid`

**Description:** Retrieve a specific voice settings preset.

**URL Parameters:**
- `uuid` (string, required): Preset UUID

**Response:**
```json
{
  "success": true,
  "data": {
    "uuid": "string",
    "name": "string",
    "settings": {
      "pace": number,
      "temperature": number,
      "pitch": number,
      "useHd": boolean,
      "exaggeration": number,
      "description": "string"
    },
    "is_public": boolean,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Create Preset

**Endpoint:** `POST /api/v2/voice_settings_presets`

**Description:** Create a new voice settings preset.

**Request Body:**
- `name` (string, required): Preset name
- `pace` (number, optional): Speech pace/speed
- `temperature` (number, optional): Voice temperature
- `pitch` (number, optional): Voice pitch
- `useHd` (boolean, optional): Use HD quality
- `exaggeration` (number, optional): Exaggeration level
- `description` (string, optional): Description or prompt

**Response:**
```json
{
  "success": true,
  "data": {
    "uuid": "string",
    "name": "string",
    "settings": object,
    "is_public": boolean,
    "created_at": "datetime",
    "updated_at": "datetime"
  },
  "message": "Preset created successfully"
}
```

### Update Preset

**Endpoint:** `PATCH /api/v2/voice_settings_presets/:uuid` or `PUT /api/v2/voice_settings_presets/:uuid`

**Description:** Update a voice settings preset.

**URL Parameters:**
- `uuid` (string, required): Preset UUID

**Request Body:**
- `name` (string, optional): Preset name
- `pace` (number, optional): Speech pace/speed
- `temperature` (number, optional): Voice temperature
- `pitch` (number, optional): Voice pitch
- `useHd` (boolean, optional): Use HD quality
- `exaggeration` (number, optional): Exaggeration level
- `description` (string, optional): Description or prompt

**Response:**
```json
{
  "success": true,
  "data": {
    "uuid": "string",
    "name": "string",
    "settings": object,
    "is_public": boolean,
    "created_at": "datetime",
    "updated_at": "datetime"
  },
  "message": "Preset updated successfully"
}
```

**Notes:**
- Can only update your own presets
- Settings are merged with existing values

### Delete Preset

**Endpoint:** `DELETE /api/v2/voice_settings_presets/:uuid`

**Description:** Delete a voice settings preset.

**URL Parameters:**
- `uuid` (string, required): Preset UUID

**Response:**
```json
{
  "success": true,
  "message": "Preset deleted successfully"
}
```

**Notes:**
- Can only delete your own presets

---

## Detect (Deepfake Detection)

Detect endpoints provide deepfake detection for audio, video, and images.

### Create Detection

**Endpoint:** `POST /api/v2/detect`

**Description:** Create a new deepfake detection job for audio, video, or image.

**Request Body:**
- `audio_token` (string, optional): Token for uploaded audio file (from secure upload)
- `media_token` (string, optional): Token for uploaded media file (from secure upload)
- `url` (string, optional): HTTPS URL to media file (alternative to token)
- `callback_url` (string, optional): HTTPS URL for completion callback
- `frame_length` (integer, optional): Frame length for analysis
- `sensitivity` (number, optional): Detection sensitivity
- `isolate_voice` (boolean, optional): Isolate voice from background
- `start_region` (number, optional): Start region for analysis (seconds)
- `end_region` (number, optional): End region for analysis (seconds)
- `max_video_fps` (integer, optional): Maximum video FPS to process
- `max_video_secs` (integer, optional): Maximum video duration to process (seconds)
- `max_limit_toggle` (boolean, optional): Enable 600-second video limit
- `use_llm` (boolean, optional): Use LLM for analysis
- `pipeline` (string, optional): Detection pipeline to use
- `visualize` (boolean, optional): Generate visualization
- `audio_source_tracing` (boolean, optional): Enable audio source tracing
- `ood_detector` (boolean, optional): Enable out-of-distribution detector
- `model_types` (array, optional): Model types to use
- `extra_params` (object, optional): Additional parameters

**Request Headers:**
- `Prefer: wait` (optional): Process synchronously and wait for results

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "status": "string (processing, completed, failed)",
    "media_type": "string (audio, video, image)",
    "url": "string",
    "filename": "string",
    "duration": number,
    "metrics": {
      "label": "string (Real, Fake)",
      "score": [number],
      "segment_labels": [string],
      "additional_metrics": object
    },
    "image_metrics": {
      "label": "string",
      "children": [
        {
          "type": "Visual Intelligence",
          "label": "string",
          "description": "string"
        }
      ]
    },
    "video_metrics": {
      "label": "string",
      "confidence": number,
      "frame_analysis": object
    },
    "audio_source_tracing": {
      "label": "string",
      "error_message": "string"
    },
    "audio_source_tracing_enabled": boolean,
    "visualize": boolean,
    "use_ood_detector": boolean,
    "pipeline": "string",
    "extra_params": object,
    "error_message": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- Either `audio_token`, `media_token`, or `url` must be provided
- URL must be HTTPS
- Media type is automatically determined from the file
- Results are processed asynchronously unless `Prefer: wait` header is used

### Get Detection

**Endpoint:** `GET /api/v2/detect/:uuid`

**Description:** Retrieve results of a deepfake detection job.

**URL Parameters:**
- `uuid` (string, required): Detection UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "status": "string",
    "media_type": "string",
    "url": "string",
    "filename": "string",
    "duration": number,
    "metrics": object,
    "image_metrics": object,
    "video_metrics": object,
    "audio_source_tracing": object,
    "error_message": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Delete Detection

**Endpoint:** `DELETE /api/v2/detect/:uuid`

**Description:** Delete a detection record.

**URL Parameters:**
- `uuid` (string, required): Detection UUID

**Response:**
```json
{
  "success": true,
  "message": "Detection was successfully deleted."
}
```

**Notes:**
- Can only delete detections from your team

### Detection Callbacks (Internal)

The following endpoints are used internally for detection callbacks:

**Audio Callback:** `POST /api/v2/detect/:uuid/callback`
**Image Callback:** `POST /api/v2/detect/:uuid/image_callback`
**Video Callback:** `POST /api/v2/detect/:uuid/video_callback`
**Audio Source Tracing Callback:** `POST /api/v2/detect/:uuid/audio_source_tracing_callback`

---

## Watermark

Watermark endpoints allow you to apply and detect audio watermarks.

### Apply Watermark

**Endpoint:** `POST /api/v2/watermark/apply`

**Description:** Apply a watermark to audio content.

**Request Body:**
- `url` (string, required): HTTPS URL to audio file (must be valid media format)
- `qr_code` (string, optional): QR code URL prefix (watermark UUID will be appended)

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "metrics": null,
    "watermarked_audio": null,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- URL must be HTTPS and point to a valid media file

### Get Watermark Apply Result

**Endpoint:** `GET /api/v2/watermark/apply/:uuid/result`

**Description:** Retrieve the result of a watermark application.

**URL Parameters:**
- `uuid` (string, required): Watermark UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "metrics": object,
    "watermarked_audio": "string (URL to watermarked file)",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Detect Watermark

**Endpoint:** `POST /api/v2/watermark/detect`

**Description:** Detect if audio contains a watermark.

**Request Body:**
- `url` (string, required): HTTPS URL to audio file (must be valid media format)

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "metrics": null,
    "watermarked_audio": null,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- URL must be HTTPS and point to a valid media file

### Get Watermark Detect Result

**Endpoint:** `GET /api/v2/watermark/detect/:uuid/result`

**Description:** Retrieve the result of watermark detection.

**URL Parameters:**
- `uuid` (string, required): Watermark UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "metrics": {
      "detected": boolean,
      "confidence": number,
      "watermark_data": object
    },
    "watermarked_audio": null,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Watermark Callbacks (Internal)

**Apply Callback:** `POST /api/v2/watermark/apply/:uuid/callback`
**Detect Callback:** `POST /api/v2/watermark/detect/:uuid/callback`

---

## Intelligence

Intelligence provides AI-powered audio content analysis and description.

### Create Intelligence

**Endpoint:** `POST /api/v2/audio_intelligence`

**Description:** Analyze audio, image, and video content using AI to generate intelligent descriptions.

**Request Body:**
- `audio_token` (string, optional): Token for uploaded audio file (from secure upload)
- `url` (string, optional): HTTPS URL to audio file
- `json` (boolean, optional): Return description as JSON. Default: false

**Response:**
```json
{
  "success": true,
  "item": {
    "description": "string or object (if json=true)",
    "created_at": "datetime"
  }
}
```

**Notes:**
- Either `audio_token` or `url` must be provided
- URL must be HTTPS if provided
- Processing is synchronous
- When `json=true`, description is parsed as JSON if possible

**Example Response (json=true):**
```json
{
  "success": true,
  "item": {
    "description": {
      "summary": "string",
      "speakers": ["string"],
      "topics": ["string"],
      "sentiment": "string",
      "key_points": ["string"]
    },
    "created_at": "datetime"
  }
}
```

---

## Speech-to-Text

Speech-to-Text endpoints provide transcription services with Q&A capabilities.

### List Transcripts

**Endpoint:** `GET /api/v2/speech-to-text`

**Description:** Retrieve a paginated list of speech transcripts for your team.

**Query Parameters:**
- `page` (integer, optional): Page number. Default: 1
- `per_page` (integer, optional): Items per page (1-50). Default: 25

**Response:**
```json
{
  "success": true,
  "meta": {
    "page": 1,
    "per_page": 25,
    "total_pages": 5,
    "total_items": 120
  },
  "items": [
    {
      "uuid": "string",
      "text": "string (full transcript)",
      "words": [
        {
          "word": "string",
          "start": number,
          "end": number,
          "confidence": number
        }
      ],
      "query": "string",
      "answer": "string",
      "status": "string (pending, processing, completed, failed)",
      "file_url": "string",
      "duration_seconds": number,
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
}
```

### Create Transcript

**Endpoint:** `POST /api/v2/speech-to-text`

**Description:** Create a new speech-to-text transcription job.

**Request Body (multipart/form-data or JSON):**
- `audio_token` (string, optional): Token for uploaded audio file (from secure upload)
- `url` (string, optional): HTTPS URL to audio/video file
- `file` (file, optional): Audio/video file upload
- `query` (string, optional): Initial question to ask about the transcript

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "text": null,
    "words": null,
    "query": "string",
    "answer": null,
    "status": "pending",
    "file_url": "string",
    "duration_seconds": number,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- One of `audio_token`, `url`, or `file` must be provided
- URL must be HTTPS if provided
- Maximum file size: 500 MB
- Maximum duration: 180 minutes (configurable)
- Processing is asynchronous
- URL download timeout: 30 seconds

### Get Transcript

**Endpoint:** `GET /api/v2/speech-to-text/:uuid`

**Description:** Retrieve a specific speech transcript.

**URL Parameters:**
- `uuid` (string, required): Transcript UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "text": "string (full transcript)",
    "words": [
      {
        "word": "string",
        "start": number,
        "end": number,
        "confidence": number
      }
    ],
    "query": "string",
    "answer": "string",
    "status": "string",
    "file_url": "string",
    "duration_seconds": number,
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

### Delete Transcript

**Endpoint:** `DELETE /api/v2/speech-to-text/:uuid`

**Description:** Delete a speech transcript.

**URL Parameters:**
- `uuid` (string, required): Transcript UUID

**Response:**
```json
{
  "success": true,
  "message": "Speech transcript deleted successfully"
}
```

### Ask Question About Transcript

**Endpoint:** `POST /api/v2/speech-to-text/:uuid/ask`

**Description:** Ask a question about a completed transcript using AI.

**URL Parameters:**
- `uuid` (string, required): Transcript UUID

**Request Body:**
- `query` (string, required): Question to ask about the transcript

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string (question UUID)",
    "query": "string",
    "answer": null,
    "status": "pending",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

**Notes:**
- Transcript must be completed and have text
- Processing is asynchronous
- Returns 202 Accepted status

### Get Question Answer

**Endpoint:** `GET /api/v2/speech-to-text/:uuid/questions/:question_uuid`

**Description:** Retrieve the answer to a question about a transcript.

**URL Parameters:**
- `uuid` (string, required): Transcript UUID
- `question_uuid` (string, required): Question UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "query": "string",
    "answer": "string",
    "status": "string (pending, processing, completed, failed)",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
}
```

---

## Identity (Speaker Identification)

Identity endpoints provide speaker identification and voice matching capabilities.

### List Identities

**Endpoint:** `GET /api/v2/identity`

**Description:** Retrieve a paginated list of speaker identities.

**Query Parameters:**
- `page` (integer, optional): Page number. Default: 1
- `search` (string, optional): Search by speaker name

**Response:**
```json
{
  "success": true,
  "page": 1,
  "total_results": 50,
  "page_count": 5,
  "items": [
    {
      "uuid": "string",
      "name": "string",
      "created_at": "datetime"
    }
  ]
}
```

**Notes:**
- Returns 10 items per page

### Create Identity

**Endpoint:** `POST /api/v2/identity`

**Description:** Create a new speaker identity from an audio sample.

**Request Body:**
- `name` (string, required): Speaker name/identifier
- `url` (string, required): URL to audio sample of the speaker

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "name": "string",
    "created_at": "datetime"
  }
}
```

**Notes:**
- URL must be accessible

### Search for Speaker

**Endpoint:** `POST /api/v2/identity/search`

**Description:** Search for matching speakers using an audio sample.

**Request Body:**
- `url` (string, required): URL to audio sample to search for
- `top_k` (integer, optional): Number of top matches to return (1-20). Default: 5

**Response:**
```json
{
  "success": true,
  "item": [
    {
      "uuid": "string",
      "name": "string",
      "confidence": number,
      "distance": number
    }
  ]
}
```

**Notes:**
- Returns the top K most similar speakers
- Results are sorted by similarity

### Delete Identity

**Endpoint:** `DELETE /api/v2/identity`

**Description:** Delete a speaker identity.

**Query Parameters:**
- `id` (string, required): Identity UUID

**Response:**
```json
{
  "success": true
}
```

**Notes:**
- Can only delete identities from your team

---

## Audio Edit

Audio Edit endpoints provide speech editing capabilities where you can modify spoken content.

### List Audio Edits

**Endpoint:** `GET /api/v2/edit`

**Description:** Retrieve a paginated list of audio edits for your team.

**Query Parameters:**
- `page` (integer, optional): Page number
- `per_page` (integer, optional): Items per page

**Response:**
```json
{
  "success": true,
  "page": 1,
  "total_results": 10,
  "page_count": 1,
  "items": [
    {
      "uuid": "string",
      "voice_uuid": "string",
      "original_transcript": "string",
      "target_transcript": "string",
      "input_audio_url": "string",
      "result_audio_url": "string",
      "error": "string"
    }
  ]
}
```

### Create Audio Edit

**Endpoint:** `POST /api/v2/edit`

**Description:** Create a new audio edit job to modify spoken content.

**Request Body:**
- `original_transcript` (string, required): Original text from the audio
- `target_transcript` (string, required): Desired modified text
- `voice_uuid` (string, required): Voice to use for synthesis
- `input_audio` (string, required): Input audio data or URL
- `callback_uri` (string, optional): Callback URL for completion notification

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "voice_uuid": "string",
    "original_transcript": "string",
    "target_transcript": "string",
    "input_audio_url": "string",
    "result_audio_url": null,
    "error": null
  }
}
```

**Notes:**
- Voice must be a non-marketplace voice owned by the user
- Processing is asynchronous
- Result will be available via GET endpoint when complete

### Get Audio Edit

**Endpoint:** `GET /api/v2/edit/:uuid`

**Description:** Retrieve the result of an audio edit job.

**URL Parameters:**
- `uuid` (string, required): Audio edit UUID

**Response:**
```json
{
  "success": true,
  "item": {
    "uuid": "string",
    "voice_uuid": "string",
    "original_transcript": "string",
    "target_transcript": "string",
    "input_audio_url": "string",
    "result_audio_url": "string (available when status=success)",
    "error": "string (present if failed)"
  }
}
```

---

## Audio Enhancements

Audio Enhancement endpoints provide audio quality improvement services.

### List Audio Enhancements

**Endpoint:** `GET /api/v2/audio_enhancements`

**Description:** Retrieve a paginated list of audio enhancements for your team.

**Query Parameters:**
- `page` (integer, optional): Page number
- `per_page` (integer, optional): Items per page

**Response:**
```json
{
  "success": true,
  "page": 1,
  "total_results": 10,
  "page_count": 1,
  "items": [
    {
      "uuid": "string",
      "status": "string (pending, processing, completed, failed)",
      "error_message": "string",
      "loudness_target_level": number,
      "loudness_peak_limit": number,
      "enhancement_level": number,
      "original_audio_url": "string",
      "enhanced_audio_url": "string"
    }
  ]
}
```

### Create Audio Enhancement

**Endpoint:** `POST /api/v2/audio_enhancements`

**Description:** Create a new audio enhancement job to improve audio quality.

**Request Body (multipart/form-data):**
- `audio_file` (file, required): Audio file to enhance (WAV, MP3, M4A, MP4, OGG, AAC, FLAC)
- `loudness_target_level` (number, optional): Target loudness level in LUFS
- `loudness_peak_limit` (number, optional): Peak loudness limit in dB
- `enhancement_level` (number, optional): Enhancement intensity level

**Response:**
```json
{
  "success": true,
  "uuid": "string",
  "status": "pending"
}
```

**Notes:**
- Maximum file size: 150 MB
- Allowed formats: WAV, MP3, M4A, MP4, OGG, AAC, FLAC
- Processing is asynchronous
- Returns 202 Accepted status

### Get Audio Enhancement

**Endpoint:** `GET /api/v2/audio_enhancements/:uuid`

**Description:** Retrieve the result of an audio enhancement job.

**URL Parameters:**
- `uuid` (string, required): Audio enhancement UUID

**Response:**
```json
{
  "success": true,
  "uuid": "string",
  "status": "string (pending, processing, completed, failed)",
  "enhanced_audio_url": "string (available when status=completed)",
  "error_message": "string (present if failed)"
}
```

---

## Voice Design

Voice Design endpoints allow you to create AI-designed voices from text prompts.

### Generate Voice Candidates

**Endpoint:** `POST /api/v2/voice-design`

**Description:** Generate voice candidates based on a text prompt describing desired voice characteristics.

**Request Body:**
- `user_prompt` (string, required): Description of desired voice (e.g., "A warm, friendly female voice with a British accent")
- `is_voice_design_trial` (boolean, optional): Whether this is a trial generation. Default: true

**Response:**
```json
{
  "voice_candidates": {
    "voice_design_model_uuid": "string",
    "samples": [
      {
        "audio_url": "string (expires in 4 hours)",
        "sample_index": integer
      }
    ]
  }
}
```

**Notes:**
- Free users are limited to one trial
- Processing is synchronous
- Returns multiple voice samples to choose from
- Audio URLs expire in 4 hours

### List Voice Designs

**Endpoint:** `GET /api/v2/voice-design`

**Description:** Retrieve all voice designs and their candidates for the current user.

**Response:**
```json
{
  "voice_designs": [
    {
      "uuid": "string",
      "prompt_text": "string",
      "preview_samples": [
        {
          "audio_url": "string (expires in 4 hours)",
          "sample_index": integer
        }
      ],
      "created_at": "datetime"
    }
  ]
}
```

### Create Rapid Voice from Design

**Endpoint:** `POST /api/v2/voice-design/:voice_design_model_uuid/:voice_sample_index/create_rapid_voice`

**Alternate Endpoint:** `POST /api/v2/voice-design/:voice_design_model_uuid/:voice_sample_index/create`

**Description:** Create a rapid voice from a selected voice design candidate.

**URL Parameters:**
- `voice_design_model_uuid` (string, required): Voice design UUID
- `voice_sample_index` (integer, required): Index of the selected sample

**Request Body:**
- `voice_name` (string, required): Name for the new voice

**Response:**
```json
{
  "voice_uuid": "string"
}
```

**Notes:**
- Returns 202 Accepted status
- Voice training begins asynchronously
- Voice design must belong to current user
- Sample must exist for the given index

### Create Voice Data (Internal)

**Endpoint:** `POST /api/v2/voice-design/:voice_design_model_uuid/:voice_sample_index/create_voice_data`

**Description:** Internal endpoint for creating voice training data from design.

**URL Parameters:**
- `voice_design_model_uuid` (string, required): Voice design UUID
- `voice_sample_index` (integer, required): Sample index

**Request Body:**
- `voice_name` (string, required): Name for the new voice

### Start Voice Design Analysis (Internal/Webhook)

**Endpoint:** `POST /api/v2/voice-design/:voice_uuid/start_analyze`

**Description:** Internal webhook endpoint for starting voice design training data generation.

**URL Parameters:**
- `voice_uuid` (string, required): Voice UUID

---

## Common Response Patterns

### Success Response
```json
{
  "success": true,
  "item": object
}
```

### Paginated Response
```json
{
  "success": true,
  "page": integer,
  "total_results": integer,
  "page_count": integer,
  "items": [object]
}
```

### Error Response
```json
{
  "success": false,
  "message": "string",
  "error": "string"
}
```

### Validation Error Response
```json
{
  "success": false,
  "error": "string",
  "validation_errors": ["string"]
}
```

---

## Authentication

All V2 API endpoints (except callbacks and internal endpoints) require authentication. Use one of the following methods:

1. **API Key Authentication**: Include your API key in the request headers:
   ```
   Authorization: Bearer YOUR_API_KEY
   ```

2. **Session Authentication**: For web-based applications, standard session cookies are used.

3. **Token Authentication**: DeviseTokenAuth tokens for mobile/SPA applications.

---

## Rate Limiting and Usage

- Character limits for synthesis depend on your plan's `characters_per_clip` setting
- Maximum characters per segment: 4000
- API access for voice creation requires Business or Enterprise plan

---

## Webhooks and Callbacks

Several endpoints support callback URLs for asynchronous operations:

- **Clips**: `callback_uri` in request enables async synthesis
- **Voices**: `callback_uri` for training completion notifications
- **Detect**: `callback_url` for detection completion
- **Audio Edits**: `callback_uri` for edit completion

Callback requests are POST requests with JSON body containing the result object.

---

## CORS Support

Some endpoints support CORS preflight requests via OPTIONS method for browser-based applications.

---

## Best Practices

1. **Use Async Operations**: For long-running tasks (synthesis, training, detection), use async mode with callbacks
2. **Implement Retry Logic**: For network errors, implement exponential backoff
3. **Cache Responses**: Cache voice lists and preset data when appropriate
4. **Monitor Quotas**: Check your plan limits and usage regularly
5. **Handle Errors Gracefully**: Always check `success` field and handle error messages
6. **Use Appropriate Sample Rates**: Choose sample rates based on your use case (e.g., 8000 for telephony, 48000 for high quality)
7. **Validate Input**: Ensure text, URLs, and files meet the documented requirements before submitting

---

## Support

For additional help:
- Email: support@resemble.ai
- Documentation: https://docs.resemble.ai
- API Status: Check service status for any ongoing issues