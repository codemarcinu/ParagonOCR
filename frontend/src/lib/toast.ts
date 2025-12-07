import toast from 'react-hot-toast';

export const showSuccess = (message: string) => {
  toast.success(message);
};

export const showError = (message: string) => {
  toast.error(message);
};

export const showInfo = (message: string) => {
  toast(message, { icon: 'ℹ️' });
};

export const showLoading = (message: string) => {
  return toast.loading(message);
};

export const updateToast = (toastId: string, message: string, type: 'success' | 'error' | 'info') => {
  toast.dismiss(toastId);
  if (type === 'success') {
    toast.success(message);
  } else if (type === 'error') {
    toast.error(message);
  } else {
    toast(message);
  }
};

