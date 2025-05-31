import path from "path";
import { fileURLToPath } from "url";
import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";

// Fix __dirname for ES module scope
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// DEBUG: Log the resolved client root folder
const clientRoot = path.resolve(__dirname, "../client");
console.log("[vite.ts] clientRoot resolved to:", clientRoot);
// Expected output: Q:\DevGenius\DevQmoi\client

import { MessageConnection, NotificationType, RequestType } from 'vscode-ws-jsonrpc';

// Example JSON-RPC request and notification types
const ExampleRequest = new RequestType<{ text: string }, { response: string }, void>('example/request');
const ExampleNotification = new NotificationType<{ message: string }>('example/notification');

export function handleJsonRpcConnection(connection: MessageConnection) {
  // Handle requests
  connection.onRequest(ExampleRequest, (params) => {
    console.log('Received example request:', params.text);
    return { response: `Server response to: ${params.text}` };
  });

  // Handle notifications
  connection.onNotification(ExampleNotification, (params) => {
    console.log('Received example notification:', params.message);
  });

  // Optionally send a notification to the client on connection
  connection.sendNotification(ExampleNotification, { message: 'Welcome to JSON-RPC server!' });
}

