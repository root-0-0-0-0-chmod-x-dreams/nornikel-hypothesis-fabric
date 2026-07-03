import { useState } from "react";
import { Modal, Button, FileInput, Input, AttentionView } from "@/components/ui";
import { Link2, Upload, Loader, Info } from "lucide-react";

interface DocumentUploadModalProps {
  open: boolean;
  onClose: () => void;
  onUploadByUrl: (url: string) => void;
  onUploadByFile: (files: File[]) => void;
  uploading?: boolean;
}

type UploadMode = "choose" | "url" | "file";

export function DocumentUploadModal({
  open,
  onClose,
  onUploadByUrl,
  onUploadByFile,
  uploading = false,
}: DocumentUploadModalProps) {
  const [mode, setMode] = useState<UploadMode>("choose");
  const [url, setUrl] = useState("");

  const handleUrlSubmit = () => {
    if (url.trim()) {
      onUploadByUrl(url.trim());
      setUrl("");
      setMode("choose");
    }
  };

  const handleFiles = (files: File[]) => {
    if (files.length > 0) {
      onUploadByFile(files);
      setMode("choose");
    }
  };

  const handleClose = () => {
    setMode("choose");
    setUrl("");
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="Добавить документ" size="md">
      {uploading ? (
        <AttentionView
          icon={<Loader size={32} className="animate-spin" />}
          title="Загружаем документ"
          description="Файл сохраняется на сервер и будет обработан для поиска."
          variant="amber"
          size="md"
          className="py-6"
        />
      ) : mode === "choose" ? (
        <div className="flex flex-col gap-3">
          <button
            onClick={() => setMode("url")}
            className="flex items-center gap-4 p-4 rounded-2xl border border-border hover:border-accent-blue-border/50 hover:bg-accent-blue-bg/30 transition-all duration-200 cursor-pointer text-left shadow-sm hover:shadow-card-hover"
          >
            <div className="p-2.5 rounded-xl bg-accent-blue-bg">
              <Link2 size={22} className="text-accent-blue" />
            </div>
            <div>
              <p className="text-sm font-medium text-text">Загрузить по ссылке</p>
              <p className="text-xs text-text-muted mt-0.5">
                Документ будет скачан с указанного URL, сохранён на сервер и обработан
              </p>
            </div>
          </button>
          <button
            onClick={() => setMode("file")}
            className="flex items-center gap-4 p-4 rounded-2xl border border-border hover:border-accent-border/50 hover:bg-accent-bg/30 transition-all duration-200 cursor-pointer text-left shadow-sm hover:shadow-card-hover"
          >
            <div className="p-2.5 rounded-xl bg-accent-bg">
              <Upload size={22} className="text-accent" />
            </div>
            <div>
              <p className="text-sm font-medium text-text">Загрузить файл</p>
              <p className="text-xs text-text-muted mt-0.5">
                PDF, DOCX, XLSX, PNG, JPG (до 50 МБ). Файл будет сохранён на сервер.
              </p>
            </div>
          </button>
          <div className="flex items-start gap-2 p-3 bg-accent-amber-bg/50 rounded-2xl border border-accent-amber-border/20 mt-1">
            <Info size={14} className="text-accent-amber mt-0.5 flex-shrink-0" />
            <p className="text-xs text-accent-amber">
              Все загруженные документы проходят предобработку: извлечение текста, структурирование
              и индексацию для поиска. Это занимает до 30 секунд.
            </p>
          </div>
        </div>
      ) : mode === "url" ? (
        <div className="flex flex-col gap-4">
          <button
            onClick={() => setMode("choose")}
            className="flex items-center gap-2 text-sm text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            ← Назад
          </button>
          <Input
            label="URL документа"
            placeholder="https://example.com/article.pdf"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleUrlSubmit()}
          />
          <p className="text-xs text-text-muted -mt-2">
            Поддерживаются прямые ссылки на PDF, DOCX, а также страницы патентов и научных публикаций.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={handleClose}>Отмена</Button>
            <Button variant="info" onClick={handleUrlSubmit} disabled={!url.trim()}>Загрузить</Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <button
            onClick={() => setMode("choose")}
            className="flex items-center gap-2 text-sm text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            ← Назад
          </button>
          <FileInput onFiles={handleFiles} />
          <p className="text-xs text-text-muted">
            Файлы будут загружены на сервер, сохранены и обработаны для полнотекстового поиска.
          </p>
        </div>
      )}
    </Modal>
  );
}
