import './styles.css';
export const metadata = { title: 'ChessCoach AI', description: 'Personal chess improvement from your real games.' };
export default function Layout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html> }
