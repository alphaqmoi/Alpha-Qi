 RenameDialog React Component (with validation & conflict resolution)
components/RenameDialog.tsx

tsx
Copy
Edit
import React, { useState } from "react";
import { Dialog, DialogTitle, DialogContent, TextField, DialogActions, Button } from "@mui/material";

type Props = {
  open: boolean;
  currentName: string;
  existingNames: string[];
  onClose: () => void;
  onRename: (newName: string) => Promise<void>;
};

export default function RenameDialog({ open, currentName, existingNames, onClose, onRename }: Props) {
  const [newName, setNewName] = useState(currentName);
  const [error, setError] = useState("");

  const handleRename = async () => {
    const trimmed = newName.trim();
    if (!trimmed) {
      setError("Name cannot be empty");
      return;
    }
    if (existingNames.includes(trimmed)) {
      setError("A file with this name already exists");
      return;
    }

    try {
      await onRename(trimmed);
      onClose();
    } catch (err: any) {
      setError("Rename failed: " + (err?.message || "Unknown error"));
    }
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Rename File</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          label="New file name"
          value={newName}
          onChange={(e) => {
            setNewName(e.target.value);
            setError("");
          }}
          error={!!error}
          helperText={error}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleRename} variant="contained">Rename</Button>
      </DialogActions>
    </Dialog>
  );
}