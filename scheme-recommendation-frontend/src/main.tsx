import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import Home from './pages/Home'

const root = createRoot(document.getElementById('root') as HTMLElement)
root.render(<Home />)
