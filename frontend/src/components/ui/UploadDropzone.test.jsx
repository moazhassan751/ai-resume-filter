import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { UploadDropzone } from './UploadDropzone'

describe('UploadDropzone', () => {
  it('calls setFile when a file is chosen', () => {
    const setFile = vi.fn()
    const { container } = render(React.createElement(UploadDropzone, { file: null, setFile }))

    const input = container.querySelector('input[type="file"]')
    const file = new File(['resume'], 'resume.pdf', { type: 'application/pdf' })

    fireEvent.change(input, { target: { files: [file] } })

    expect(setFile).toHaveBeenCalledWith(file)
    expect(screen.getByRole('button', { name: 'Choose file' })).toBeInTheDocument()
  })
})