import React, { useState } from 'react';
import { startAuthentication } from '@simplewebauthn/browser';
import { getPasskeyAuthenticationOptions, verifyPasskeyAuthentication } from '../lib/api';
import { useAuthStore } from '../store/authStore';
import { fetchMe } from '../lib/api';
import { Button } from './ui';

interface PasskeyLoginProps {
  username?: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
  className?: string;
}

const PasskeyLogin: React.FC<PasskeyLoginProps> = ({
  username,
  onSuccess,
  onError,
  className,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login: loginAction } = useAuthStore();

  const handleLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      // Check if WebAuthn is supported
      if (!window.PublicKeyCredential) {
        throw new Error('WebAuthn nie jest obsługiwane w tej przeglądarce');
      }

      // Get authentication options from server
      const options = await getPasskeyAuthenticationOptions(username);

      // Start authentication using SimpleWebAuthn
      const credential = await startAuthentication(options);

      // Verify authentication with server
      const tokenData = await verifyPasskeyAuthentication({
        credential,
        challenge: options.challenge,
      });

      const token = tokenData.access_token;

      // Set token and fetch user
      useAuthStore.getState().setToken(token);
      const user = await fetchMe();
      loginAction(token, user);

      onSuccess?.();
    } catch (err: any) {
      let errorMessage = 'Nie udało się uwierzytelnić za pomocą klucza dostępu';
      
      if (err.name === 'NotSupportedError') {
        errorMessage = 'Klucze dostępu nie są obsługiwane na tym urządzeniu. Użyj innej metody uwierzytelniania.';
      } else if (err.name === 'NotAllowedError' || err.message?.includes('timeout') || err.message?.includes('not allowed')) {
        errorMessage = 'Operacja została anulowana, przekroczono limit czasu lub nie została dozwolona. Spróbuj ponownie i upewnij się, że ukończysz monit biometryczny.';
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      onError?.(errorMessage);
      
      console.error('Passkey authentication error:', err);
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
        onClick={handleLogin}
        disabled={loading}
        isLoading={loading}
        className="w-full"
        size="lg"
        variant="secondary"
      >
        {loading ? 'Uwierzytelnianie...' : 'Zaloguj się Kluczem Dostępu'}
      </Button>
      <p className="mt-2 text-xs text-gray-500">
        Użyj biometrii swojego urządzenia, aby się zalogować
      </p>
    </div>
  );
};

export default PasskeyLogin;
export { PasskeyLogin };

