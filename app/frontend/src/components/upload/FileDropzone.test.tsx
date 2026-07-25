import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { FileDropzone } from './FileDropzone';

describe('FileDropzone', () => {
  it('selects a CSV file and shows metadata', async () => {
    const user = userEvent.setup();
    const onFileChange = vi.fn();
    render(<FileDropzone file={null} onFileChange={onFileChange} />);

    const input = screen.getByLabelText(/browse csv/i);
    const file = new File(['MD,GR,X,Y,Z,TVT_input\n1,1,1,1,1,1\n'], 'well.csv', {
      type: 'text/csv',
    });
    await user.upload(input, file);

    expect(onFileChange).toHaveBeenCalledWith(file);
  });

  it('rejects non-CSV files', async () => {
    const onFileChange = vi.fn();
    render(<FileDropzone file={null} onFileChange={onFileChange} />);

    const input = screen.getByLabelText(/browse csv/i);
    const file = new File(['nope'], 'well.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFileChange).toHaveBeenCalledWith(null);
    expect(screen.getByRole('alert')).toHaveTextContent(/only \.csv/i);
  });

  it('removes a selected file', async () => {
    const user = userEvent.setup();
    const onFileChange = vi.fn();
    const file = new File(['MD,GR,X,Y,Z,TVT_input\n1,1,1,1,1,\n'], 'well.csv', {
      type: 'text/csv',
    });
    render(<FileDropzone file={file} onFileChange={onFileChange} />);

    await user.click(screen.getByRole('button', { name: /remove file/i }));
    expect(onFileChange).toHaveBeenCalledWith(null);
  });

  it('exposes a labeled file input', () => {
    render(<FileDropzone file={null} onFileChange={vi.fn()} />);
    expect(screen.getByLabelText(/browse csv/i)).toBeInTheDocument();
  });
});
