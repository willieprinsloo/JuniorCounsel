'use client';

/**
 * Application Sidebar
 *
 * Navigation menu for authenticated users.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  label: string;
  href: string;
  icon?: string;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Cases', href: '/cases' },
  { label: 'Documents', href: '/documents' },
  { label: 'Drafts', href: '/drafts' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-50 border-r border-gray-200 min-h-screen">
      <nav className="p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                block px-4 py-2 text-sm font-medium rounded-md transition-colors
                ${
                  isActive
                    ? 'bg-blue-100 text-blue-900'
                    : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                }
              `}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
