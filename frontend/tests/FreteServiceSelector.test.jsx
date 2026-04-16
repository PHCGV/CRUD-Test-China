import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import FreteServiceSelector from '../src/components/FreteServiceSelector'

const filters = [
  { id: 'all', label: 'Todos os servicos' },
  { id: 'cssbuy', label: 'Cssbuy' },
  { id: 'hoobuy', label: 'Hoobuy' },
  { id: 'acbuy', label: 'Acbuy' },
]

describe('FreteServiceSelector', () => {
  it('renderiza as opcoes de servico', () => {
    render(<FreteServiceSelector filters={filters} value="all" onChange={() => {}} />)

    const select = screen.getByLabelText('Servico de compra')
    expect(select).toBeInTheDocument()

    for (const option of filters) {
      expect(screen.getByRole('option', { name: option.label })).toBeInTheDocument()
    }
  })

  it('dispara callback quando servico muda', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(<FreteServiceSelector filters={filters} value="all" onChange={onChange} />)

    const select = screen.getByLabelText('Servico de compra')
    await user.selectOptions(select, 'hoobuy')

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('hoobuy')
    })
  })
})
