'use client';

/**
 * Reusable Confirmation Dialog Component
 *
 * A modal dialog for confirming destructive actions like deletions.
 * Supports light/dark mode.
 */

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  const variantStyles = {
    danger: 'bg-destructive hover:bg-destructive/90 focus:ring-destructive text-destructive-foreground',
    warning: 'bg-secondary hover:bg-secondary/90 focus:ring-secondary text-secondary-foreground',
    info: 'bg-primary hover:bg-primary/90 focus:ring-primary text-primary-foreground',
  };

  const iconBgStyles = {
    danger: 'bg-destructive/10',
    warning: 'bg-secondary/10',
    info: 'bg-primary/10',
  };

  const iconStyles = {
    danger: 'text-destructive',
    warning: 'text-secondary',
    info: 'text-primary',
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />

        {/* Dialog */}
        <div className="relative transform overflow-hidden rounded-lg bg-card border border-border text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
          <div className="bg-card px-4 pb-4 pt-5 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div
                className={`mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full ${iconBgStyles[variant]} sm:mx-0 sm:h-10 sm:w-10`}
              >
                <svg
                  className={`h-6 w-6 ${iconStyles[variant]}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                  />
                </svg>
              </div>
              <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                <h3 className="text-base font-semibold leading-6 text-card-foreground">
                  {title}
                </h3>
                <div className="mt-2">
                  <p className="text-sm text-muted-foreground">{message}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-muted/50 px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6 gap-2">
            <button
              type="button"
              onClick={onConfirm}
              className={`inline-flex w-full justify-center rounded-md px-4 py-2 text-sm font-semibold shadow-sm transition-colors ${variantStyles[variant]} focus:outline-none focus:ring-2 focus:ring-offset-2 sm:w-auto`}
            >
              {confirmText}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex w-full justify-center rounded-md bg-card px-4 py-2 text-sm font-semibold text-card-foreground shadow-sm border border-border hover:bg-accent transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring sm:w-auto"
            >
              {cancelText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
