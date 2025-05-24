import { useState, useEffect } from "react";
import { useAuth } from "./useAuth";
import { useToast } from "@/components/ui/use-toast";

export interface AIModel {
  id: string;
  name: string;
  type: "code" | "chat" | "completion";
  status: "active" | "inactive" | "error";
  parameters: {
    size?: number;
    quantization_config?: {
      load_in_8bit?: boolean;
      load_in_4bit?: boolean;
      bnb_4bit_compute_dtype?: string;
      bnb_4bit_use_double_quant?: boolean;
      bnb_4bit_quant_type?: string;
    };
    generation?: {
      max_length?: number;
      temperature?: number;
      top_p?: number;
      top_k?: number;
      repetition_penalty?: number;
    };
  };
}

export function useModels() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [loading, setLoading] = useState(true);

  // Load models
  useEffect(() => {
    if (!user) return;

    const loadModels = async () => {
      try {
        const response = await fetch("/api/ai/models", {
          headers: {
            Authorization: `Bearer ${user.token}`,
          },
        });

        const data = await response.json();
        if (data.status === "success") {
          setModels(data.models);

          // Select first active model by default
          const activeModel = data.models.find(
            (m: AIModel) => m.status === "active",
          );
          if (activeModel) {
            setSelectedModel(activeModel);
          }
        } else {
          throw new Error(data.message);
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load AI models",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };

    loadModels();
  }, [user]);

  // Load model
  const loadModel = async (modelId: string) => {
    if (!user) return;

    try {
      const response = await fetch(`/api/ai/models/${modelId}/load`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${user.token}`,
        },
      });

      const data = await response.json();
      if (data.status === "success") {
        // Update model status
        setModels((prev) =>
          prev.map((model) =>
            model.id === modelId ? { ...model, status: "active" } : model,
          ),
        );

        // Select model if not already selected
        if (!selectedModel || selectedModel.id !== modelId) {
          const model = models.find((m) => m.id === modelId);
          if (model) {
            setSelectedModel(model);
          }
        }
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load AI model",
        variant: "destructive",
      });
    }
  };

  // Unload model
  const unloadModel = async (modelId: string) => {
    if (!user) return;

    try {
      const response = await fetch(`/api/ai/models/${modelId}/unload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${user.token}`,
        },
      });

      const data = await response.json();
      if (data.status === "success") {
        // Update model status
        setModels((prev) =>
          prev.map((model) =>
            model.id === modelId ? { ...model, status: "inactive" } : model,
          ),
        );

        // Deselect model if currently selected
        if (selectedModel?.id === modelId) {
          setSelectedModel(null);
        }
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to unload AI model",
        variant: "destructive",
      });
    }
  };

  return {
    models,
    selectedModel,
    setSelectedModel,
    loading,
    loadModel,
    unloadModel,
  };
}
