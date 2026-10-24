'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
export default function Navigation() {
 const path=usePathname(); const [account,setAccount]=useState<any>(null);
 useEffect(()=>{ if(localStorage.getItem('token')) api.get('/api/auth/me').then(r=>setAccount(r.data)).catch(()=>setAccount(null)); },[path]);
 return <div className="border-t border-border px-6 py-3 flex flex-wrap items-center gap-2">
 { [['/','Analysis'],['/scanner','Scanner'],['/history','History'],['/glossary','Glossary'],['/subscribe','Pro membership'],['/admin','Admin']].map(([href,label])=><Link key={href} href={href} className={'btn '+(path===href?'btn-primary':'btn-secondary')}>{label}</Link>)}
 {account && <span className="text-xs text-muted ml-auto">{account.user.name} · <span className={'badge badge-'+account.user.role}>{account.user.role.toUpperCase()}</span> · {account.usage_today} analyses today</span>}
 </div>;
}
