# Multi-Agent Video System

## Overview

The Multi-Agent Video System is an AI-powered video creation platform built on Google's Agent Development Kit (ADK) framework. The system automates the entire video production pipeline from text prompt to finished video by orchestrating multiple specialized agents that handle research, scriptwriting, asset sourcing, voiceover generation, and video assembly.

![Multi-Agent Video System Architecture](docs/architecture.png)

This system leverages ADK's agent coordination capabilities to manage specialized agents for different aspects of video production, providing a seamless end-to-end video creation experience.

## Agent Details

| Attribute         | Details                                                                                                                                                                                             |
| :---------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Interaction Type** | Conversational                                                                                                                                                                                      |
| **Complexity**    | Advanced                                                                                                                                                                                            |
| **Agent Type**    | Multi-Agent System                                                                                                                                                                                  |
| **Components**    | Tools, Multi-Agent Orchestration, External APIs, Video Processing                                                                                                                                   |
| **Vertical**      | Content Creation                                                                                                                                                                                    |

### Agent Architecture

The system consists of the following specialized agents:

1. **Root Orchestrator Agent** - Main coordinator that manages the video creation workflow
2. **Research Agent** - Gathers information and context for video content using web search APIs
3. **Story Agent** - Creates scripts and narrative structure from research data
4. **Asset Sourcing Agent** - Finds visual assets from stock media providers (Pexels, Unsplash, Pixabay)
5. **Image Generation Agent** - Generates custom images using AI when stock assets are insufficient
6. **Audio Agent** - Handles text-to-speech conversion and audio processing
7. **Video Assembly Agent** - Combines all elements into final video using FFmpeg

### Key Features

* **End-to-End Automation:** Complete video creation from text prompt to finished video
* **Multi-Agent Orchestration:** Specialized agents handle different aspects of production
* **External API Integration:** Leverages multiple APIs for research, assets, and AI generation
* **Flexible Asset Sourcing:** Combines stock media with AI-generated content
* **Professional Quality:** Produces high-quality videos with proper synchronization
* **Scalable Architecture:** Built on ADK framework for enterprise deployment

## Setup and Installation Instructions

### Prerequisites

* **Google Cloud Account:** You need a Google Cloud account with appropriate permissions
* **Python 3.11+:** Ensure you have Python 3.11 or a later version installed
* **Poetry:** Install Poetry by following the instructions on the official Poetry website: [https://python-poetry.org/docs/](https://python-poetry.org/docs/)
* **FFmpeg:** Install FFmpeg for video processing capabilities
* **Git:** Ensure you have git installed

### Project Setup with Poetry

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/google/adk-samples.git
   cd adk-samples/python/agents/multi-agent-video-system
   ```

2. **Install Dependencies with Poetry:**

   ```bash
   poetry install
   ```

   This command reads the `pyproject.toml` file and installs all the necessary dependencies into a virtual environment managed by Poetry.

3. **Activate the Poetry Shell:**

   ```bash
   poetry shell
   ```

   This activates the virtual environment, allowing you to run commands within the project's environment.

4. **Set up Environment Variables:**
   
   Copy the `.env.example` file to `.env` and fill in your API keys and configuration:
   
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file with your actual values for:
   - Google Cloud credentials
   - External API keys (Serper, Pexels, Unsplash, etc.)
   - AI service API keys (OpenAI, ElevenLabs, etc.)

## Running the Agent

You can run the agent using the ADK command in your terminal from the root project directory:

1. **Run agent in CLI:**

   ```bash
   adk run video_system
   ```

2. **Run agent with ADK Web UI:**
   
   ```bash
   adk web
   ```
   
   Select the Multi-Agent Video System from the dropdown

### Example Interaction

Here's a quick example of how a user might interact with the agent:

**Example: Video Generation Request**

User: Create a 60-second video about "The benefits of renewable energy"

Agent: I'll create a comprehensive video about renewable energy benefits. Let me start by researching the topic, then create a script, source appropriate visuals, generate voiceover, and assemble the final video.

[The system then orchestrates all agents to produce the final video]

## Evaluating the Agent

The evaluation can be run from the `multi-agent-video-system` directory using the `pytest` module:

```bash
poetry run pytest eval
```

### Evaluation Process

The evaluation framework consists of:

1. **test_eval.py**: Main test script using `AgentEvaluator` from Google ADK
2. **conversation.test.json**: Test cases structured as conversations with expected outputs
3. **test_config.json**: Evaluation criteria and thresholds for performance assessment

## Deploying the Agent

The Agent can be deployed to Vertex AI Agent Engine using:

```bash
python deployment/deploy.py
```

After deployment, update your `.env` file with the returned Agent Engine ID and test the deployed agent:

```bash
python deployment/run.py
```

## Architecture Details

### Agent Communication Flow

```
Text Prompt → Root Orchestrator → Research Agent → Story Agent → Asset Sourcing Agent
                                                                        ↓
Video Assembly Agent ← Audio Agent ← [Asset Collection Complete]
```

### External Integrations

- **Research:** Serper API, Brave Search API
- **Stock Media:** Pexels, Unsplash, Pixabay APIs
- **AI Generation:** OpenAI DALL-E, Stability AI
- **Text-to-Speech:** ElevenLabs, Google Cloud TTS
- **Video Processing:** FFmpeg

## Customization

### Adding New Agents

You can extend the system by adding new specialized agents in the `sub_agents/` directory following the ADK agent pattern.

### Modifying Workflows

Update the root orchestrator in `video_system/agent.py` to modify the video creation workflow.

### External API Integration

Add new tools in the respective agent's `tools/` directory to integrate additional external services.

## Troubleshooting

### Common Issues

1. **API Key Errors:** Ensure all required API keys are set in your `.env` file
2. **FFmpeg Not Found:** Install FFmpeg and ensure it's in your system PATH
3. **Memory Issues:** Large video processing may require increased system resources
4. **Rate Limiting:** Some APIs have rate limits; the system includes retry logic

### Debugging

Enable debug logging by setting the log level in your environment:

```bash
export LOG_LEVEL=DEBUG
```

## Disclaimer

This agent sample is provided for illustrative purposes only and is not intended for production use. It serves as a foundational starting point for developing video generation systems.

This sample has not been rigorously tested for production environments and may require additional security hardening, error handling, scalability improvements, and performance optimizations before deployment in critical systems.

Users are responsible for thorough testing, security review, and compliance with applicable regulations before using any derived system in production environments.