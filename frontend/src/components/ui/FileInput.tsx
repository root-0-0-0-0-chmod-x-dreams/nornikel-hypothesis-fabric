import { useRef, type ChangeEvent, type DragEvent, useState } from "react";
import { Upload, File } from "lucide-react";

interface FileInputProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  label?: string;
  className?: string;
}

export function FileInput({ onFiles, accept, multiple = true, label = "Перетащите файлы или нажмите для загрузки", className = "" }: FileInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    onFiles(Array.from(files));
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleDrag = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(e.type === "dragover" || e.type === "dragenter");
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div
      onDragOver={handleDrag}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-3 p-8 border-2 border-dashed
        rounded-xl cursor-pointer transition-all duration-150
        ${dragOver ? "border-accent bg-accent-bg" : "border-border hover:border-accent-border/50 hover:bg-gray-50"}
        ${className}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
        className="hidden"
      />
      <div className={`p-3 rounded-full ${dragOver ? "bg-accent-bg" : "bg-gray-100"}`}>
        {dragOver ? <File size={24} className="text-accent" /> : <Upload size={24} className="text-text-muted" />}
      </div>
      <p className="text-sm text-text-muted text-center">{label}</p>
      <p className="text-xs text-text-muted/60">
        PDF, DOCX, XLSX, PNG, JPG (до 50 МБ)
      </p>
    </div>
  );
}
