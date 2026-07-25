import { useForm } from 'react-hook-form';
import { validateOptionalWellId } from '../../utils/schemas';

interface WellIdFormValues {
  wellId: string;
}

interface WellIdFieldProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  label?: string;
  placeholder?: string;
}

export function WellIdField({
  value,
  onChange,
  disabled = false,
  label = 'Optional custom well ID',
  placeholder = 'Leave blank to use filename',
}: WellIdFieldProps) {
  const { register, setValue } = useForm<WellIdFormValues>({
    mode: 'onChange',
    defaultValues: { wellId: value },
    values: { wellId: value },
  });

  const error = validateOptionalWellId(value);

  return (
    <div className="field" style={{ maxWidth: '22rem' }}>
      <label htmlFor="well-id-field">{label}</label>
      <input
        id="well-id-field"
        disabled={disabled}
        placeholder={placeholder}
        aria-invalid={!!error && value.trim() !== ''}
        {...register('wellId', {
          onChange: (event) => {
            const next = event.target.value;
            setValue('wellId', next, { shouldValidate: true });
            onChange(next);
          },
        })}
      />
      {error && value.trim() !== '' ? (
        <p className="help-text" role="alert">
          {error}
        </p>
      ) : (
        <p className="help-text">
          Use a safe identifier such as letters, numbers, underscore, dot, or
          hyphen.
        </p>
      )}
    </div>
  );
}
