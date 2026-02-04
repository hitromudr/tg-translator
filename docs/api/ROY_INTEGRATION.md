# Roy AI Bridge Integration Guide

This document describes how to integrate the **Roy Messenger Backend (Go)** with the local **AI Service (Python)**.

## Overview

The AI Service runs as a local HTTP server (`sidecar`) on the same host.
It exposes a REST API to offload heavy ML tasks:
1.  **Smart Translation** (Llama 3 / Google)
2.  **Speech-to-Text** (Whisper V3 / Local)
3.  **Text-to-Speech** (Silero)

## Connection Details

*   **Base URL**: `http://127.0.0.1:8090`
*   **Protocol**: HTTP/1.1
*   **Authentication**: None (Localhost only)

---

## Endpoints

### 1. Translation (`/translate`)

Translates text using context-aware AI.

**Request:** `POST /translate`
```json
{
  "text": "Hey bro, wazzup?",
  "source_lang": "en",
  "target_lang": "ru"
}
```

**Response:** `200 OK`
```json
{
  "translation": "Здарова, братан, чё как?",
  "source": "en",
  "target": "ru"
}
```

---

### 2. Speech-to-Text (`/stt`)

Transcribes voice messages. Supports OGG (Opus), MP3, WAV.

**Request:** `POST /stt`
*   **Headers**: `Content-Type: multipart/form-data`
*   **Body**: Form file field named `file`.

**Response:** `200 OK`
```json
{
  "text": "Привет, это проверка связи."
}
```

---

### 3. Text-to-Speech (`/tts`)

Generates voice audio from text.

**Request:** `POST /tts`
```json
{
  "text": "Привет, Рой!",
  "lang": "ru",
  "gender": "female"
}
```
*   **Supported Languages**: `ru`, `en`, `de`, `es`, `fr`.
*   **Gender**: `male`, `female`.

**Response:** `200 OK`
*   **Content-Type**: `audio/mpeg`
*   **Body**: Binary MP3 data.

---

## Golang Implementation Example

Copy this snippet into your Go project (`pkg/ai/client.go`):

```go
package ai

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
)

const ServiceURL = "http://127.0.0.1:8090"

type TranslateResponse struct {
	Translation string `json:"translation"`
}

type STTResponse struct {
	Text string `json:"text"`
}

// Translate text
func Translate(text, src, tgt string) (string, error) {
	payload := map[string]string{
		"text":        text,
		"source_lang": src,
		"target_lang": tgt,
	}
	body, _ := json.Marshal(payload)

	resp, err := http.Post(ServiceURL+"/translate", "application/json", bytes.NewBuffer(body))
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("API Error: %s", resp.Status)
	}

	var res TranslateResponse
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return "", err
	}
	return res.Translation, nil
}

// Transcribe audio file
func Transcribe(filePath string) (string, error) {
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	
	// Add file
	file, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer file.Close()
	
	part, err := writer.CreateFormFile("file", filePath)
	if err != nil {
		return "", err
	}
	io.Copy(part, file)
	writer.Close()

	resp, err := http.Post(ServiceURL+"/stt", writer.FormDataContentType(), body)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("API Error: %s", resp.Status)
	}

	var res STTResponse
	if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
		return "", err
	}
	return res.Text, nil
}
```
