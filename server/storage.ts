import { 
  User, 
  InsertUser, 
  File, 
  InsertFile, 
  Project, 
  InsertProject, 
  ChatMessage, 
  InsertChatMessage, 
  Deployment, 
  InsertDeployment
} from "@shared/schema";

export interface IStorage {
  // User operations
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  // File operations
  getFile(id: number): Promise<File | undefined>;
  getFilesByUserId(userId: number): Promise<File[]>;
  createFile(file: InsertFile): Promise<File>;
  updateFileContent(id: number, content: string): Promise<File | undefined>;
  
  // Project operations
  getProject(id: number): Promise<Project | undefined>;
  getProjectsByUserId(userId: number): Promise<Project[]>;
  createProject(project: InsertProject): Promise<Project>;
  
  // Chat operations
  getChatMessagesByUserId(userId: number, projectId?: number): Promise<ChatMessage[]>;
  createChatMessage(message: InsertChatMessage): Promise<ChatMessage>;
  
  // Deployment operations
  getDeployment(id: number): Promise<Deployment | undefined>;
  getDeploymentsByUserId(userId: number, projectId?: number): Promise<Deployment[]>;
  createDeployment(deployment: InsertDeployment): Promise<Deployment>;
  updateDeploymentStatus(id: number, status: string, url?: string, logs?: string): Promise<Deployment | undefined>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private files: Map<number, File>;
  private projects: Map<number, Project>;
  private chatMessages: Map<number, ChatMessage>;
  private deployments: Map<number, Deployment>;
  
  private userId: number = 1;
  private fileId: number = 1;
  private projectId: number = 1;
  private chatMessageId: number = 1;
  private deploymentId: number = 1;

  constructor() {
    this.users = new Map();
    this.files = new Map();
    this.projects = new Map();
    this.chatMessages = new Map();
    this.deployments = new Map();
    
    // Create a default user
    this.createUser({
      username: "demo",
      password: "password",
      email: "demo@example.com"
    });
    
    // Create a default project
    this.createProject({
      userId: 1,
      name: "Alpha-Q AI Demo",
      description: "A demo project for Alpha-Q AI"
    });
  }

  // User operations
  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.userId++;
    const timestamp = new Date();
    const user: User = { 
      ...insertUser, 
      id,
      createdAt: timestamp
    };
    this.users.set(id, user);
    return user;
  }
  
  // File operations
  async getFile(id: number): Promise<File | undefined> {
    return this.files.get(id);
  }
  
  async getFilesByUserId(userId: number): Promise<File[]> {
    return Array.from(this.files.values()).filter(
      (file) => file.userId === userId
    );
  }
  
  async createFile(insertFile: InsertFile): Promise<File> {
    const id = this.fileId++;
    const timestamp = new Date();
    const file: File = {
      ...insertFile,
      id,
      createdAt: timestamp,
      updatedAt: timestamp
    };
    this.files.set(id, file);
    return file;
  }
  
  async updateFileContent(id: number, content: string): Promise<File | undefined> {
    const file = this.files.get(id);
    
    if (!file) return undefined;
    
    const updatedFile: File = {
      ...file,
      content,
      updatedAt: new Date()
    };
    
    this.files.set(id, updatedFile);
    return updatedFile;
  }
  
  // Project operations
  async getProject(id: number): Promise<Project | undefined> {
    return this.projects.get(id);
  }
  
  async getProjectsByUserId(userId: number): Promise<Project[]> {
    return Array.from(this.projects.values()).filter(
      (project) => project.userId === userId
    );
  }
  
  async createProject(insertProject: InsertProject): Promise<Project> {
    const id = this.projectId++;
    const timestamp = new Date();
    const project: Project = {
      ...insertProject,
      id,
      createdAt: timestamp,
      updatedAt: timestamp
    };
    this.projects.set(id, project);
    return project;
  }
  
  // Chat operations
  async getChatMessagesByUserId(userId: number, projectId?: number): Promise<ChatMessage[]> {
    return Array.from(this.chatMessages.values())
      .filter((message) => {
        if (message.userId !== userId) return false;
        if (projectId !== undefined && message.projectId !== projectId) return false;
        return true;
      })
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }
  
  async createChatMessage(insertMessage: InsertChatMessage): Promise<ChatMessage> {
    const id = this.chatMessageId++;
    const timestamp = new Date();
    const message: ChatMessage = {
      ...insertMessage,
      id,
      timestamp
    };
    this.chatMessages.set(id, message);
    return message;
  }
  
  // Deployment operations
  async getDeployment(id: number): Promise<Deployment | undefined> {
    return this.deployments.get(id);
  }
  
  async getDeploymentsByUserId(userId: number, projectId?: number): Promise<Deployment[]> {
    return Array.from(this.deployments.values())
      .filter((deployment) => {
        if (deployment.userId !== userId) return false;
        if (projectId !== undefined && deployment.projectId !== projectId) return false;
        return true;
      })
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }
  
  async createDeployment(insertDeployment: InsertDeployment): Promise<Deployment> {
    const id = this.deploymentId++;
    const timestamp = new Date();
    const deployment: Deployment = {
      ...insertDeployment,
      id,
      timestamp
    };
    this.deployments.set(id, deployment);
    return deployment;
  }
  
  async updateDeploymentStatus(id: number, status: string, url?: string, logs?: string): Promise<Deployment | undefined> {
    const deployment = this.deployments.get(id);
    
    if (!deployment) return undefined;
    
    const updatedDeployment: Deployment = {
      ...deployment,
      status,
      ...(url && { url }),
      ...(logs && { logs: deployment.logs ? `${deployment.logs}\n${logs}` : logs })
    };
    
    this.deployments.set(id, updatedDeployment);
    return updatedDeployment;
  }
}

export const storage = new MemStorage();
