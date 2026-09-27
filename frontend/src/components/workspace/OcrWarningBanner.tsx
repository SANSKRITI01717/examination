import React from 'react'
import { Button } from '../ui/Button'

interface OcrWarningBannerProps {
  confidence: number
  reviewRequired: boolean
  isVerified: boolean
  onVerify: () => void
  isSubmitting?: boolean
}

export const OcrWarningBanner: React.FC<OcrWarningBannerProps> = ({
  confidence,
  reviewRequired,
  isVerified,
  onVerify,
  isSubmitting = false,
}) => {
  if (!reviewRequired || isVerified) return null

  return (
    <div className="bg-amber-50 border-l-4 border-amber-500 p-3.5 rounded-r-xl shadow-xs mb-3">
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="p-1 rounded-full bg-amber-100 text-amber-700">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wide">
              Human verification needed (OCR confidence: {Math.round(confidence * 100)}%)
            </h4>
            <p className="text-xs text-amber-800 mt-0.5">
              Handwriting confidence is below threshold. Please review the OCR text against the scanned image before accepting AI marks.
            </p>
          </div>
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={onVerify}
          isLoading={isSubmitting}
          className="bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 font-semibold"
        >
          ✓ Confirm text as correct
        </Button>
      </div>
    </div>
  )
}
