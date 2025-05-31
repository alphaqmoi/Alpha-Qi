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
