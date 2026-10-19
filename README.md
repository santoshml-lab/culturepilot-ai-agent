CulturePilot AI

Discover Your Next Favorite Thing with AI

CulturePilot AI is a Qloo-powered cultural discovery application that helps users explore personalized recommendations across movies, music, food, travel, and other experiences.

Live Demo

- Frontend: https://culturepilot-ai.vercel.app/
- Backend: https://culturepilot-ai-agent.onrender.com/

Features

- Explore recommendations across multiple cultural categories.
- Use personal interests to guide discovery.
- Integrate Qloo's cultural intelligence API.
- Run a multi-agent workflow with Planner, Researcher, Recommender, Reviewer, and Executor stages.
- Discover new experiences through an interactive web interface.

Technology Stack

- Python
- Qloo API
- FastAPI (if used by the backend)
- Vercel for frontend deployment
- Render for backend deployment

How It Works

1. The user selects a category and enters their interests.
2. The workflow plans the recommendation task.
3. The research stage retrieves relevant information using the available Qloo integration.
4. The recommendation stage prepares personalized suggestions.
5. The review stage checks the recommendations before they are presented to the user.

Qloo Integration

CulturePilot AI uses the Qloo API to retrieve cultural intelligence and support personalized discovery. The backend uses the "QLOO_API_KEY" environment variable to authenticate API requests.

Never commit API keys or other secrets to the repository.

Local Setup

1. Clone this repository.
2. Install the dependencies listed in the project's dependency file.
3. Configure the required environment variables, including "QLOO_API_KEY".
4. Start the backend using the project's documented startup command.
5. Open the frontend and configure its backend URL as needed.

Refer to the source files and dependency configuration for the exact commands required by this project.

Project Status

CulturePilot AI is an active project developed for the Qloo Agentic Hackathon.

License

The open-source license will be added in the "LICENSE" file.

Acknowledgments

Thanks to Qloo for providing cultural intelligence technology for this project.
