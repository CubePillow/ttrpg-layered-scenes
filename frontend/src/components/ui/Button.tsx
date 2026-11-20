import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from 'react'
import { cx } from './cx'
import styles from './Button.module.css'

type Variant = 'default' | 'primary'

type LinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; variant?: Variant }
type ActionProps = ButtonHTMLAttributes<HTMLButtonElement> & { href?: undefined; variant?: Variant }

/** Pixel button. Pass `href` to get a link that looks like a button. */
export default function Button(props: LinkProps | ActionProps) {
  if (props.href !== undefined) {
    const { variant = 'default', className, ...rest } = props
    return <a data-variant={variant} className={cx(styles.button, variant === 'primary' && styles.primary, className)} {...rest} />
  }
  const { variant = 'default', className, type = 'button', ...rest } = props
  return <button type={type} data-variant={variant} className={cx(styles.button, variant === 'primary' && styles.primary, className)} {...rest} />
}
