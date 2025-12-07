import { Link, useNavigate } from 'react-router-dom';
import { Home, ArrowLeft, Receipt } from 'lucide-react';
import { ReceiptUploader } from '@/components/ReceiptUploader';
import { Button } from '@/components/ui';

export function UploadReceipt() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <Link 
              to="/" 
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              title="Powrót do strony głównej"
            >
              <Home className="h-5 w-5" />
            </Link>
            <div className="flex items-center space-x-3">
              <Receipt className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Skanuj Paragon
              </h1>
            </div>
          </div>
          <Button
            onClick={() => navigate('/receipts')}
            variant="secondary"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
          >
            Zobacz Paragony
          </Button>
        </div>

        {/* Info Section */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-8">
          <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-200 mb-2">
            Jak dodać paragon?
          </h2>
          <ul className="list-disc list-inside space-y-1 text-sm text-blue-800 dark:text-blue-300">
            <li>Przeciągnij i upuść plik paragonu w obszarze poniżej</li>
            <li>Lub kliknij, aby wybrać plik z komputera</li>
            <li>Obsługiwane formaty: PDF, PNG, JPG, TIFF (max 10MB)</li>
            <li>Paragon zostanie automatycznie przetworzony przez OCR i AI</li>
          </ul>
        </div>

        {/* Upload Component */}
        <ReceiptUploader />

        {/* Success Message */}
        <div className="mt-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Po przesłaniu paragonu zostaniesz przekierowany do listy paragonów
          </p>
        </div>
      </div>
    </div>
  );
}

