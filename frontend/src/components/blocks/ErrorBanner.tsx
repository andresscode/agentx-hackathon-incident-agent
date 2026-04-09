import { AlertCircle, AlertTriangle, X, XCircle } from 'lucide-react'
import Link from 'next/link'

type ErrorType = 'payment' | 'restricted-item'

interface ErrorBannerProps {
  errorType: ErrorType
  onDismiss: () => void
  onReportIssue?: () => void
}

const ERROR_CONTENT = {
  payment: {
    title: 'Payment Processing Failed',
    message:
      'We encountered an error while processing your payment. This could be due to network issues, invalid payment information, or a system error. Please try again or contact support if the problem persists.',
    showReportButton: true,
    icon: AlertCircle,
  },
  'restricted-item': {
    title: 'Failed to Add Item to Cart',
    message:
      'We encountered a system error while attempting to add this item to your cart. This could be due to a database synchronization issue, cache inconsistency, or service disruption. Please try again or report this issue if the problem persists.',
    showReportButton: true,
    icon: XCircle,
  },
}

export function ErrorBanner({ errorType, onDismiss }: ErrorBannerProps) {
  const content = ERROR_CONTENT[errorType]
  const Icon = content.icon

  return (
    <div className="bg-red-50 border-2 border-red-200 rounded-lg">
      <div className="px-6 py-4">
        <div className="flex items-start gap-3">
          <Icon className="w-6 h-6 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-red-900 mb-1">{content.title}</h3>
            <p className="text-sm text-red-800 mb-3">{content.message}</p>
            {content.showReportButton && (
              <Link
                href="/incidents/create"
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition-colors"
              >
                <AlertTriangle className="w-4 h-4" />
                Report This Issue
              </Link>
            )}
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="text-red-600 hover:text-red-800 shrink-0"
            aria-label="Dismiss error"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
