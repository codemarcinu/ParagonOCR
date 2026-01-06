/**
 * Receipt Upload Component with drag-drop and WebSocket progress.
 */

import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useReceiptStore } from '@/store/receiptStore';
import { WS_BASE_URL } from '@/lib/api';
import { Button } from '@/components/ui';

interface ProcessingStage {
  stage: 'idle' | 'uploading' | 'ocr' | 'llm' | 'saving' | 'completed' | 'error';
  progress: number;
  message: string;
}

export function ReceiptUploader() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [stage, setStage] = useState<ProcessingStage>({
    stage: 'idle',
    progress: 0,
    message: '',
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { uploadReceipt, error, clearError } = useReceiptStore();

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      clearError();

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        await handleFileUpload(files[0]);
      }
    },
    [clearError]
  );

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        clearError();
        await handleFileUpload(files[0]);
      }
    },
    [clearError]
  );

  const handleFileUpload = async (file: File) => {
    // Validate file type
    const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'];
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
      setStage({
        stage: 'error',
        progress: 0,
        message: `Nieprawidłowy typ pliku. Dozwolone: ${allowedExtensions.join(', ')}`,
      });
      return;
    }

    // Validate file size (10 MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      setStage({
        stage: 'error',
        progress: 0,
        message: `Plik zbyt duży. Maksymalny rozmiar: ${maxSize / 1024 / 1024} MB`,
      });
      return;
    }

    try {
      setStage({ stage: 'uploading', progress: 10, message: 'Analizowanie pliku...' });

      // Client-Side PDF Text Extraction
      if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
        try {
          const pdfjsLib = await import('pdfjs-dist');
          // Set worker src
          pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

          const arrayBuffer = await file.arrayBuffer();
          const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
          const pdf = await loadingTask.promise;
          let fullText = '';

          for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const textContent = await page.getTextContent();
            const pageText = textContent.items.map((item: any) => item.str).join(' ');
            fullText += pageText + '\n';
          }

          if (fullText.length > 50) {
            console.log("PDF Text extracted client-side:", fullText.length, "chars");
            setStage({ stage: 'uploading', progress: 30, message: 'Wysyłanie tekstu...' });
            const { ingestReceiptText } = await import('@/lib/api');
            const result = await ingestReceiptText(fullText);
            await monitorProcessing(result.receipt_id);
            return;
          }
        } catch (pdfError) {
          console.warn("Client-side PDF extraction failed, falling back to server OCR:", pdfError);
          // Fallback to normal upload
        }
      }

      setStage({ stage: 'uploading', progress: 10, message: 'Przesyłanie pliku...' });

      // Upload file
      const result = await uploadReceipt(file);
      await monitorProcessing(result.receipt_id);

    } catch (err) {
      setStage({
        stage: 'error',
        progress: 0,
        message: err instanceof Error ? err.message : 'Nie udało się przesłać paragonu',
      });
    }
  };

  const monitorProcessing = async (receiptId: number) => {
    // Connect to WebSocket for real-time updates
    const wsUrl = `${WS_BASE_URL}/api/receipts/ws/processing/${receiptId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to processing WebSocket');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'update') {
        setStage({
          stage: data.stage as any, // Cast to stage type
          progress: data.progress,
          message: data.message,
        });

        if (data.stage === 'completed') {
          ws.close();
          // Redirect to receipts list after successful upload
          setTimeout(() => {
            setStage({ stage: 'idle', progress: 0, message: '' });
            if (fileInputRef.current) {
              fileInputRef.current.value = '';
            }
            // Trigger refresh if needed (e.g. reload receipts list)
            window.dispatchEvent(new Event('receipt-uploaded'));
            // Navigate to receipts list after 2 seconds
            setTimeout(() => {
              navigate('/receipts');
            }, 2000);
          }, 3000);
        }
      } else if (data.status === 'error') {
        setStage({
          stage: 'error',
          progress: 0,
          message: data.message || data.error || 'Unknown error',
        });
        ws.close();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Don't necessarily fail UI if WS fails, might just lose progress updates
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };
  };

  const handleRetry = () => {
    setStage({ stage: 'idle', progress: 0, message: '' });
    clearError();
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${isDragging
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
          aria-describedby="file-upload-help"
          aria-label="Prześlij plik paragonu"
        />

        {stage.stage === 'idle' && (
          <>
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
              aria-hidden="true"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-4h4m-4-4v4m0 4v4m0-4h4m-4-4h4"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div className="mt-4">
              <label htmlFor="file-upload" className="cursor-pointer inline-block">
                <span className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 pointer-events-none">
                  Wybierz plik
                </span>
              </label>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                lub przeciągnij i upuść
              </p>
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400" id="file-upload-help">
              PDF, PNG, JPG, TIFF do 10MB
            </p>
          </>
        )}

        {(stage.stage === 'uploading' ||
          stage.stage === 'ocr' ||
          stage.stage === 'llm' ||
          stage.stage === 'saving') && (
            <>
              <div className="mb-4" role="status" aria-live="polite" aria-atomic="true">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {stage.message}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400" aria-label={`Postęp: ${stage.progress} procent`}>
                    {stage.progress}%
                  </span>
                </div>
                <div
                  className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700"
                  role="progressbar"
                  aria-valuenow={stage.progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={stage.message}
                >
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${stage.progress}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center justify-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" aria-hidden="true" />
                <span>Przetwarzanie...</span>
              </div>
            </>
          )}

        {stage.stage === 'completed' && (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 dark:bg-green-900">
              <svg
                className="h-6 w-6 text-green-600 dark:text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <p className="mt-4 text-sm font-medium text-green-600 dark:text-green-400">
              {stage.message}
            </p>
          </div>
        )}

        {stage.stage === 'error' && (
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 dark:bg-red-900">
              <svg
                className="h-6 w-6 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <p className="mt-4 text-sm font-medium text-red-600 dark:text-red-400">
              {stage.message}
            </p>
            {error && (
              <p className="mt-2 text-xs text-red-500 dark:text-red-400">{error}</p>
            )}
            <Button
              onClick={handleRetry}
              className="mt-4"
            >
              Spróbuj Ponownie
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

