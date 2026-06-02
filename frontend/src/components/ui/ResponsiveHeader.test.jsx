import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { ResponsiveHeader } from './ResponsiveHeader'

describe('ResponsiveHeader', () => {
  it('toggles the mobile navigation menu', () => {
    const onLogout = vi.fn()

    render(React.createElement(ResponsiveHeader, {
      title: 'Dashboard',
      links: [
        { href: '/dashboard', label: 'Dashboard' },
        { href: '/upload', label: 'Upload' },
      ],
      onLogout,
    }))

    expect(screen.getByRole('button', { name: 'Toggle navigation menu' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Toggle navigation menu' }))
    expect(screen.getAllByRole('link', { name: 'Upload' })).toHaveLength(2)
    fireEvent.click(screen.getAllByRole('button', { name: 'Logout' })[0])
    expect(onLogout).toHaveBeenCalled()
  })
})