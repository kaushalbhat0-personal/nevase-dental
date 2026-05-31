import { FormProvider } from 'react-hook-form';
import type { FormWrapperProps } from './types';

export function FormWrapper<TFieldValues extends Record<string, unknown>, TTransformedValues extends Record<string, unknown> = TFieldValues>({
  form,
  onSubmit,
  children,
  submitLabel = 'Submit',
  loadingLabel = 'Submitting...',
  className = '',
  apiError,
}: FormWrapperProps<TFieldValues, TTransformedValues>) {
  const {
    handleSubmit,
    formState: { isSubmitting },
  } = form;

  const onFormSubmit = handleSubmit(async (data) => {
    console.log('SUBMIT TRIGGERED');
    await onSubmit(data);
  });

  return (
    <FormProvider {...form}>
      <form onSubmit={onFormSubmit} className={`space-y-6 ${className}`}>
        {apiError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {apiError}
          </div>
        )}

        {children}

        <button
          type="submit"
          disabled={isSubmitting}
          className="min-h-[44px] px-6 py-2.5 inline-flex items-center justify-center gap-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <svg
                className="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>{loadingLabel}</span>
            </>
          ) : (
            <span>{submitLabel}</span>
          )}
        </button>
      </form>
    </FormProvider>
  );
}
