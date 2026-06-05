import { NavLink, Outlet } from 'react-router-dom'
import { UserButton } from '@clerk/clerk-react'
import { BarChart2, Users, Settings, CreditCard, LayoutDashboard } from 'lucide-react'
import { cn } from '@/lib/utils'
import ThemeToggle from '@/components/ThemeToggle'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/competitors', label: 'Competidores', icon: Users },
  { to: '/settings', label: 'Configuración', icon: Settings },
  { to: '/settings/billing', label: 'Plan y facturación', icon: CreditCard },
]

export default function AppLayout() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 border-r bg-background flex flex-col shrink-0">
        <div className="h-14 flex items-center px-4 border-b">
          <span className="font-bold text-primary flex items-center gap-1">
            <BarChart2 className="h-5 w-5" />
            vigi.ai
          </span>
        </div>
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/settings'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t flex items-center justify-between">
          <UserButton afterSignOutUrl="/login" />
          <ThemeToggle />
        </div>
      </aside>

      {/* Contenido principal */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
