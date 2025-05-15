# MyScript Integration Overview

## Introduction

InkLink supports handwriting recognition using MyScript's advanced recognition technology through their Web API. This enables converting handwritten notes from your reMarkable tablet to text, facilitating search, processing, and integration with other services.

## Architecture

The integration uses the following components:

1. `HandwritingWebAdapter` - Core adapter that communicates with the MyScript Cloud API
2. `HandwritingAdapter` - Wrapper that provides a consistent interface for the application
3. `HandwritingRecognitionService` - Service layer that orchestrates the recognition process

## API Details

The integration uses the following MyScript Cloud API endpoints:

- Main endpoint: `https://cloud.myscript.com/api/v4.0/iink/`
- Recognition endpoint: `recognize`

## Features

The MyScript integration provides the following capabilities:

- Text recognition from handwritten notes
- Math expression recognition
- Diagram and drawing recognition
- Multi-page document processing
- Cross-page context for improved accuracy

## Content Types

The API supports various content types for recognition:

- **Text** - General handwritten text
- **Math** - Mathematical expressions and equations
- **Diagram** - Drawings, diagrams, and charts

## References

- [MyScript Developer Documentation](https://developer.myscript.com/docs)
- [MyScript Cloud API Documentation](https://cloud.myscript.com/api/v4.0/iink/batch/api-docs)
- [MyScript Developer Portal](https://developer.myscript.com/)