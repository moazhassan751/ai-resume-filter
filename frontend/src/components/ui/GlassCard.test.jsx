import React from 'react'
import { render, screen } from '@testing-library/react'
import { GlassCard } from './GlassCard'

describe('GlassCard', () => {
  it('renders title, subtitle, and children', () => {
    render(React.createElement(GlassCard, { title: 'Dashboard', subtitle: 'Overview panel' }, React.createElement('div', null, 'Content body')))

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Overview panel')).toBeInTheDocument()
    expect(screen.getByText('Content body')).toBeInTheDocument()
  })
})