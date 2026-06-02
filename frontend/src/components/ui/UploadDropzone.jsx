import { useRef, useState } from 'react'
import { motion } from 'framer-motion'

export function UploadDropzone({ file, setFile, hint = 'Drop a resume PDF, image, or DOCX here' }) {
  const inputRef = useRef(null)
  const [active, setActive] = useState(false)

  const handleDrop = (event) => {
    event.preventDefault()
    setActive(false)
    const dropped = event.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }

  return (
    <motion.div
      onDragOver={(event) => { event.preventDefault(); setActive(true) }}
      onDragLeave={() => setActive(false)}
      onDrop={handleDrop}
      whileHover={{ scale: 1.01 }}
      className={`glass-card rounded-3xl border border-dashed p-6 transition ${active ? 'border-cyan-300/70 bg-cyan-400/10' : 'border-white/15 bg-white/5'}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.tif,.tiff"
        className="hidden"
        onChange={(event) => setFile(event.target.files?.[0] || null)}
      />
      <div className="flex flex-col items-stretch justify-center gap-3 text-center sm:items-center">
        <div className="rounded-full bg-white/10 px-4 py-2 text-xs uppercase tracking-[0.24em] text-cyan-200">Drag & drop</div>
        <p className="text-sm text-slate-300">{hint}</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="w-full rounded-full bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 sm:w-auto"
        >
          Choose file
        </button>
        {file && <p className="text-xs text-slate-400">Selected: {file.name}</p>}
      </div>
    </motion.div>
  )
}