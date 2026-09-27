import React, { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import { ConfidenceBadge } from './ConfidenceBadge'
import { OcrWarningBanner } from './OcrWarningBanner'
import type { OcrStatus } from '../../lib/constants'

interface OcrPanelProps {
  ocr: {
    status: OcrStatus
    text: string
    verified_text: string | null
    confidence: number | null
    review_required: boolean
    verified: boolean
  }
  onSaveText: (text: string, verify: boolean) => Promise<void>
  onRerunOcr?: () => Promise<void>
  isRerunningOcr?: boolean
  readOnly?: boolean
}

export const OcrPanel: React.FC<OcrPanelProps> = ({
  ocr,
  onSaveText,
  onRerunOcr,
  isRerunningOcr = false,
  readOnly = false,
}) => {
  const [currentText, setCurrentText] = useState(ocr.verified_text || ocr.text || '')
  const [isSaving, setIsSaving] = useState(false)
  const isDirty = currentText !== (ocr.verified_text || ocr.text || '')

  useEffect(() => {
    setCurrentText(ocr.verified_text || ocr.text || '')
  }, [ocr.verified_text, ocr.text])

  const handleSave = async (markVerified: boolean = false) => {
    setIsSaving(true)
    try {
      await onSaveText(currentText, markVerified || ocr.verified)
    } finally {
      setIsSaving(false)
    }
  }

  const handleVerify = async () => {
    setIsSaving(true)
    try {
      await onSaveText(currentText, true)
    } finally {
      setIsSaving(false)
    }
  }

  const wordCount = currentText.trim() ? currentText.trim().split(/\s+/).length : 0
  const charCount = currentText.length

  const getStatusBadge = () => {
    switch (ocr.status) {
      case 'done':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            Done
          </span>
        )
      case 'processing':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
            Processing...
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            Failed
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            Pending
          </span>
        )
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            OCR Extracted Text
          </h4>
          {getStatusBadge()}
          {ocr.verified && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              ✓ Verified
            </span>
          )}
        </div>
        <ConfidenceBadge confidence={ocr.confidence} label="OCR Conf" />
      </div>

      <OcrWarningBanner
        confidence={ocr.confidence ?? 0}
        reviewRequired={ocr.review_required}
        isVerified={ocr.verified}
        onVerify={handleVerify}
        isSubmitting={isSaving}
      />

      <div className="relative">
        <textarea
          rows={5}
          readOnly={readOnly}
          value={currentText}
          onChange={e => setCurrentText(e.target.value)}
          placeholder={ocr.status === 'processing' ? 'Digitizing handwriting via Vision OCR...' : 'No text extracted...'}
          className={`w-full p-3 rounded-lg border text-sm font-mono text-slate-800 bg-slate-50/50 leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all ${
            ocr.review_required && !ocr.verified
              ? 'border-amber-300 ring-1 ring-amber-200'
              : 'border-slate-200'
          }`}
        />
        <div className="absolute bottom-2 right-2 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-white/80 rounded backdrop-blur-xs pointer-events-none">
          {wordCount} words · {charCount} chars
        </div>
      </div>

      {!readOnly && (
        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <div className="flex items-center space-x-2">
            <span>{isDirty ? '● Unsaved edits' : '✓ Synchronized with server'}</span>
            {!ocr.verified && (
              <span className="hidden sm:inline text-[10px] text-slate-400 font-mono">
                [V] to verify
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {onRerunOcr && (
              <Button
                size="sm"
                variant="outline"
                onClick={onRerunOcr}
                isLoading={isRerunningOcr}
                title="Trigger fresh OCR scan from the page image (O2)"
              >
                ↻ Re-run OCR
              </Button>
            )}
            {isDirty && (
              <Button
                size="sm"
                variant="primary"
                onClick={() => handleSave(true)}
                isLoading={isSaving}
              >
                Save & Verify Text
              </Button>
            )}
            {!ocr.verified && !isDirty && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleVerify}
                isLoading={isSaving}
              >
                Confirm Verified
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
