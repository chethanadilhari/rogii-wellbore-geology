import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { ManualWellTable } from './ManualWellTable';
import type { ManualWellRow } from '../../types/well';
import { createEmptyManualRow } from '../../utils/manualWell';

function Harness({ initialRows = [] as ManualWellRow[] }) {
  const [rows, setRows] = useState(initialRows);
  const [wellId, setWellId] = useState('manual_well');
  return (
    <ManualWellTable
      wellId={wellId}
      onWellIdChange={setWellId}
      rows={rows}
      onRowsChange={setRows}
    />
  );
}

describe('ManualWellTable', () => {
  it('adds and removes rows', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole('button', { name: /add row/i }));
    expect(screen.getByLabelText(/md row 1/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /remove row 1/i }));
    expect(screen.queryByLabelText(/md row 1/i)).not.toBeInTheDocument();
  });

  it('edits numeric cells and marks empty TVT as prediction rows', async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initialRows={[
          createEmptyManualRow({
            MD: 1,
            GR: 1,
            X: 1,
            Y: 1,
            Z: 1,
            TVT_input: 10,
          }),
        ]}
      />,
    );

    const tvt = screen.getByLabelText(/tvt_input row 1/i);
    await user.clear(tvt);
    const row = tvt.closest('tr');
    expect(row?.className).toMatch(/prediction-row/);
  });

  it('loads an example known-then-missing pattern', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: /load example/i }));
    expect(screen.getByLabelText('MD row 1')).toBeInTheDocument();
    expect(screen.getByLabelText('TVT_input row 13')).toHaveValue('');
  });
});
