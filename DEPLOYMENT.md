# Deployment Guide

This guide covers different deployment options for the AI Chat Application.

## Prerequisites

- Docker and Docker Compose installed
- Node.js 16+ (for local development)
- Python 3.9+ (for local development)
- Hugging Face API token

## Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Create a `.env` file in the root directory:
   ```
   HUGGINGFACE_TOKEN=your_token_here
   MODEL_NAME=gpt2
   MAX_LENGTH=100
   TEMPERATURE=0.7
   ```

3. Start the application using Docker Compose:
   ```bash
   docker-compose up --build
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000

## Production Deployment

### Option 1: Docker Deployment

1. Build and run using Docker Compose:
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

2. Monitor logs:
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

### Option 2: Cloud Deployment

#### AWS Elastic Beanstalk

1. Install the EB CLI:
   ```bash
   pip install awsebcli
   ```

2. Initialize EB application:
   ```bash
   eb init
   ```

3. Create environment:
   ```bash
   eb create production
   ```

4. Deploy:
   ```bash
   eb deploy
   ```

#### Heroku

1. Install Heroku CLI:
   ```bash
   # For Windows (using scoop)
   scoop install heroku
   # For macOS
   brew install heroku
   ```

2. Login to Heroku:
   ```bash
   heroku login
   ```

3. Create Heroku app:
   ```bash
   heroku create your-app-name
   ```

4. Set environment variables:
   ```bash
   heroku config:set HUGGINGFACE_TOKEN=your_token_here
   heroku config:set MODEL_NAME=gpt2
   ```

5. Deploy:
   ```bash
   git push heroku main
   ```

## Monitoring and Maintenance

### Logs

- Docker logs:
  ```bash
  docker-compose logs -f
  ```

- Application logs:
  ```bash
  tail -f conversation_history/app.log
  ```

### Backup

1. Backup conversation history:
   ```bash
   tar -czf conversation_history_backup.tar.gz conversation_history/
   ```

2. Backup model checkpoints:
   ```bash
   tar -czf checkpoints_backup.tar.gz checkpoints/
   ```

### Scaling

1. Increase workers:
   ```bash
   # Edit docker-compose.yml
   command: gunicorn --workers 8 --bind 0.0.0.0:5000 main:app
   ```

2. Add load balancer:
   ```bash
   # Example using Nginx
   upstream backend {
       server backend1:5000;
       server backend2:5000;
   }
   ```

## Security Considerations

1. Always use HTTPS in production
2. Keep your Hugging Face token secure
3. Implement rate limiting
4. Regular security updates
5. Monitor system resources

## Troubleshooting

1. Check container status:
   ```bash
   docker-compose ps
   ```

2. View container logs:
   ```bash
   docker-compose logs <service-name>
   ```

3. Restart services:
   ```bash
   docker-compose restart
   ```

4. Common issues:
   - Port conflicts: Change ports in docker-compose.yml
   - Memory issues: Adjust worker count
   - API errors: Check Hugging Face token

## Support

For issues and support:
1. Check the logs
2. Review the documentation
3. Create an issue in the repository
4. Contact the development team
