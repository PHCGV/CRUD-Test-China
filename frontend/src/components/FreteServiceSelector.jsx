import React from 'react'

function FreteServiceSelector({ filters, value, onChange }) {
  return (
    <section className="frete-filter-row" aria-label="Filtro por servico">
      <label htmlFor="freteServiceFilter" className="frete-filter-label">Servico de compra</label>
      <select
        id="freteServiceFilter"
        className="frete-filter-select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {filters.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
    </section>
  )
}

export default FreteServiceSelector
