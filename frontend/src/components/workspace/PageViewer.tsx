import React, { useState } from 'react'
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch'

interface PageViewerProps {
  pages: { id: number; page_number: number; image_url: string }[]
}

export const PageViewer: React.FC<PageViewerProps> = ({ pages }) => {
  const [currentPageIndex, setCurrentPageIndex] = useState(0)

  if (!pages || pages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-100 rounded-xl border border-slate-200 text-slate-400 text-sm p-8">
        No scanned pages available
      </div>
    )
  }

  const activePage = pages[currentPageIndex] || pages[0]

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl overflow-hidden border border-slate-800 shadow-inner">
      {/* Top Toolbar: Controls & Page Tabs */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950 border-b border-slate-800 text-xs text-white z-10">
        {/* Page selector */}
        <div className="flex items-center space-x-1">
          <span className="text-slate-400 font-semibold mr-2 uppercase tracking-wider text-[11px]">Pages:</span>
          {pages.map((p, idx) => (
            <button
              key={p.id}
              onClick={() => setCurrentPageIndex(idx)}
              className={`px-2.5 py-1 rounded text-xs font-semibold cursor-pointer transition-colors ${
                idx === currentPageIndex
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              Page {p.page_number}
            </button>
          ))}
        </div>

        {/* Zoom controls hook into TransformWrapper controls */}
        <div className="text-slate-400 text-[11px] hidden sm:block">
          Scroll or drag to pan & zoom
        </div>
      </div>

      {/* Main Pan / Zoom Viewport */}
      <div className="flex-1 relative overflow-hidden flex items-center justify-center p-2 bg-slate-900/90">
        <TransformWrapper
          initialScale={1}
          minScale={0.5}
          maxScale={4}
          centerOnInit={true}
        >
          {({ zoomIn, zoomOut, resetTransform }) => (
            <>
              {/* Floating zoom control buttons */}
              <div className="absolute bottom-4 right-4 z-20 flex items-center space-x-1.5 bg-slate-950/80 backdrop-blur-md p-1.5 rounded-xl border border-slate-700/60 shadow-lg">
                <button
                  onClick={() => zoomIn()}
                  title="Zoom In"
                  className="p-1.5 text-slate-200 hover:text-white hover:bg-slate-800 rounded-lg cursor-pointer"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
                <button
                  onClick={() => zoomOut()}
                  title="Zoom Out"
                  className="p-1.5 text-slate-200 hover:text-white hover:bg-slate-800 rounded-lg cursor-pointer"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                  </svg>
                </button>
                <button
                  onClick={() => resetTransform()}
                  title="Reset Scale"
                  className="px-2 py-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg text-xs font-medium cursor-pointer"
                >
                  Fit
                </button>
              </div>

              <TransformComponent
                wrapperClass="!w-full !h-full flex items-center justify-center"
                contentClass="flex items-center justify-center"
              >
                <img
                  src={activePage.image_url}
                  alt={`Answer page ${activePage.page_number}`}
                  className="max-h-[75vh] max-w-full object-contain rounded shadow-2xl transition-transform"
                />
              </TransformComponent>
            </>
          )}
        </TransformWrapper>
      </div>
    </div>
  )
}
