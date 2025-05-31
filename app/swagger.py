from flasgger import Swagger

def register_swagger(app):
    Swagger(app, template={
        "swagger": "2.0",
        "info": {
            "title": "AlphaQ API",
            "description": "AI Model Management API",
            "version": "1.0.0"
        },
        "basePath": "/",
        "schemes": ["http"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer {token}'"
            }
        }
    })