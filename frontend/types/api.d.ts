// API Response Types
export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
}

// User Types
export interface User {
    id: number;
    username: string;
    email: string;
    is_admin: boolean;
    created_at: string;
    last_login: string;
}

// Project Types
export interface Project {
    id: number;
    name: string;
    description: string;
    app_type: 'web' | 'mobile' | 'api';
    framework: string;
    created_at: string;
    updated_at: string;
    user_id: number;
}

// Chat Types
export interface ChatMessage {
    id: number;
    timestamp: string;
    role: 'user' | 'assistant';
    content: string;
    model_id: number;
    user_id: number;
    tokens_used: number;
    processing_time: number;
    status: 'success' | 'error' | 'timeout';
}

// Model Types
export interface Model {
    id: number;
    name: string;
    type: 'llm' | 'embedding' | 'classification';
    status: 'inactive' | 'active' | 'error';
    is_active: boolean;
    parameters: Record<string, any>;
    quantization_config?: Record<string, any>;
    device_map?: string;
    max_memory?: Record<string, any>;
    offload_folder?: string;
    is_cloud_enabled: boolean;
    cloud_config?: Record<string, any>;
    optimization_level?: string;
    cache_dir?: string;
    created_at: string;
    updated_at: string;
    last_used?: string;
}

// System Types
export interface SystemMetrics {
    timestamp: string;
    cpu_percent: number;
    memory_percent: number;
    gpu_utilization?: number;
    disk_usage: number;
    network_io: {
        bytes_sent: number;
        bytes_recv: number;
        packets_sent: number;
        packets_recv: number;
        errin: number;
        errout: number;
        dropin: number;
        dropout: number;
    };
}

export interface SystemAlert {
    type: 'cpu' | 'memory' | 'gpu' | 'disk';
    message: string;
    timestamp: string;
}

// Voice Types
export interface VoiceModel {
    id: number;
    name: string;
    type: 'stt' | 'tts';
    model_id: string;
    processor_id?: string;
    parameters?: Record<string, any>;
    status: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    last_used?: string;
}

export interface VoiceSession {
    id: number;
    session_id: string;
    user_id: number;
    stt_model_id?: number;
    tts_model_id?: number;
    start_time: string;
    end_time?: string;
    status: string;
    parameters?: Record<string, any>;
}

// File Types
export interface FileVersion {
    id: number;
    file_id: number;
    version: number;
    content: string;
    hash: string;
    created_at: string;
    created_by: number;
    comment?: string;
}

export interface FileComment {
    id: number;
    file_id: number;
    user_id: number;
    content: string;
    created_at: string;
    parent_id?: number;
    replies?: FileComment[];
}

export interface FilePermission {
    id: number;
    file_id: number;
    user_id: number;
    permission: 'read' | 'write' | 'admin';
    created_at: string;
    created_by: number;
} 