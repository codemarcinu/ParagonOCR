import React, { useState } from 'react';
import { startRegistration } from '@simplewebauthn/browser';
import { getPasskeyRegistrationOptions, verifyPasskeyRegistration } from '../lib/api';
import { Button } from './ui';

interface PasskeyRegistrationProps {
  deviceName?: string;
  onSuccess?: (tokenData?: any) => void;
  onError?: (error: string) => void;
  className?: string;
}

const PasskeyRegistration: React.FC<PasskeyRegistrationProps> = ({
  deviceName,
  onSuccess,
  onError,
  className,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegister = async () => {
    setLoading(true);
    setError(null);

    try {
      // Check if WebAuthn is supported
      if (!window.PublicKeyCredential) {
        throw new Error('WebAuthn nie jest obsługiwane w tej przeglądarce');
      }

      // Get registration options from server
      const options = await getPasskeyRegistrationOptions(deviceName);

      // Start registration using SimpleWebAuthn
      const credential = await startRegistration(options as any);

      // Verify registration with server
      const result = await verifyPasskeyRegistration({
        credential,
        challenge: options.challenge,
      });

      if (result.success || result.access_token) {
        // Pass token data to onSuccess callback
        onSuccess?.(result);
      } else {
        throw new Error(result.message || 'Rejestracja nie powiodła się');
      }
    } catch (err: any) {
      let errorMessage = 'Nie udało się zarejestrować klucza dostępu';

      if (err.name === 'NotSupportedError') {
        errorMessage = 'Klucze dostępu nie są obsługiwane na tym urządzeniu. Użyj innej metody uwierzytelniania.';
      } else if (err.name === 'NotAllowedError' || err.message?.includes('timeout') || err.message?.includes('not allowed')) {
        errorMessage = 'Operacja została anulowana, przekroczono limit czasu lub nie została dozwolona. Spróbuj ponownie i upewnij się, że ukończysz monit biometryczny.';
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
      onError?.(errorMessage);

      console.error('Passkey registration error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={className}>
      {error && (
        <div className="mb-4 rounded bg-red-100 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <Button
        type="button"
        onClick={handleRegister}
        disabled={loading}
        isLoading={loading}
        className="w-full"
        size="lg"
      >
        {loading ? 'Rejestrowanie Klucza Dostępu...' : 'Zarejestruj Klucz Dostępu'}
      </Button>
      <p className="mt-2 text-xs text-gray-500">
        Użyj biometrii swojego urządzenia (Face ID, Touch ID, Windows Hello, itp.)
      </p>
    </div>
  );
};

export default PasskeyRegistration;

