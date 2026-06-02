import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToastProvider, useToast } from './ToastProvider'

function ToastButton() {
  const { toast } = useToast()
  return React.createElement('button', { onClick: () => toast('Saved successfully') }, 'Notify')
}

describe('ToastProvider', () => {
  it('shows a toast message from a child consumer', async () => {
    render(React.createElement(ToastProvider, null, React.createElement(ToastButton)))

    fireEvent.click(screen.getByRole('button', { name: 'Notify' }))

    expect(await screen.findByText('Saved successfully')).toBeInTheDocument()
  })
})