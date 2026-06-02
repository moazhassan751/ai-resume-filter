import React from 'react'
import '@testing-library/jest-dom'
import { vi } from 'vitest'

vi.mock('framer-motion', () => {
  const passthrough = (tag) => {
    const Component = ({ children, whileHover, initial, animate, exit, transition, variants, layout, ...props }) => React.createElement(tag, props, children)
    return Component
  }

  return {
    AnimatePresence: ({ children }) => React.createElement(React.Fragment, null, children),
    motion: new Proxy({}, {
      get: (_, tag) => passthrough(tag),
    }),
  }
});