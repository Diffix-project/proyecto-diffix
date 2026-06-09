import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion, useInView, useMotionValue, useTransform, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { BarChart3, TrendingUp, Bell, Shield, Sparkles, ArrowRight, Check, Bot, Search, FileText, Globe, Zap, MousePointer2, Activity } from 'lucide-react'

/* ─────────────── helpers ─────────────── */

function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

function useCountUp(end: number, duration = 2) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })
  const [val, setVal] = useState(0)

  useEffect(() => {
    if (!inView) return
    let start = 0
    const step = Math.ceil(end / (duration * 60))
    const timer = setInterval(() => {
      start += step
      if (start >= end) { setVal(end); clearInterval(timer) }
      else setVal(start)
    }, 1000 / 60)
    return () => clearInterval(timer)
  }, [inView, end, duration])

  return { ref, val, inView }
}

/* ─── card con efecto de brillo que sigue el mouse ─── */

function GlowCard({ children, className = '', ...props }: React.HTMLAttributes<HTMLDivElement> & { children: React.ReactNode }) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [isHovered, setIsHovered] = useState(false)

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
  }, [])

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn('relative overflow-hidden rounded-2xl border border-border/40 bg-card/30 backdrop-blur-sm transition-colors duration-500 hover:border-primary/30', className)}
      {...props}
    >
      {isHovered && (
        <div
          className="pointer-events-none absolute -inset-px z-0 opacity-100 transition-opacity duration-300"
          style={{
            background: `radial-gradient(400px circle at ${mousePos.x}px ${mousePos.y}px, hsl(var(--primary) / 0.06), transparent 60%)`,
          }}
        />
      )}
      <div className="relative z-10">{children}</div>
    </div>
  )
}

/* ─── barra animada del dashboard mockup ─── */

function AnimatedBar({ height, delay }: { height: string; delay: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })
  return (
    <div ref={ref} className="flex-1 bg-muted/60 rounded-sm relative overflow-hidden" style={{ height }}>
      <motion.div
        className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-primary to-accent/60 rounded-sm"
        initial={{ height: 0 }}
        animate={inView ? { height: '100%' } : { height: 0 }}
        transition={{ duration: 0.8, delay, ease: 'easeOut' }}
      />
    </div>
  )
}

/* ─────────────── ticker data ─────────────── */

const tickerItems = [
  { label: 'Distribuidora del Centro bajó precios 12%', type: 'alerta' },
  { label: 'Nuevo producto: Kit Industrial X500', type: 'novedad' },
  { label: 'Stock agotado: Filtros A-200', type: 'oportunidad' },
  { label: 'Remate preventa: 30% OFF en línea blanca', type: 'alerta' },
  { label: 'Distribuidora Norte actualizó catálogo', type: 'novedad' },
  { label: 'Precio mínimo del mercado bajó 5%', type: 'inteligencia' },
  { label: '3 competidores nuevos en tu zona', type: 'alerta' },
  { label: 'Promoción flash: 2x1 en lubricantes', type: 'oportunidad' },
]

const tickerTypeStyles: Record<string, string> = {
  alerta: 'bg-red-500/15 text-red-400 border-red-500/25',
  novedad: 'bg-primary/15 text-primary border-primary/25',
  oportunidad: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
  inteligencia: 'bg-blue-500/15 text-blue-400 border-blue-500/25',
}

/* ─────────────── nav ─────────────── */

function Nav() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className={cn(
        'fixed top-0 inset-x-0 z-50 transition-all duration-500',
        scrolled
          ? 'bg-background/70 backdrop-blur-2xl border-b border-border/50 shadow-sm'
          : 'bg-transparent',
      )}
    >
      <div className="mx-auto max-w-7xl flex items-center justify-between px-6 h-16">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="size-9 rounded-xl bg-gradient-to-br from-primary to-accent/80 flex items-center justify-center shadow-lg shadow-primary/20 group-hover:shadow-primary/40 transition-shadow">
            <BarChart3 className="size-5 text-primary-foreground" />
          </div>
          <span className="font-serif text-xl tracking-tight">
            Diffi<span className="text-primary">X</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm">
          {[
            { label: 'Cómo funciona', href: '#como-funciona' },
            { label: 'Qué detectamos', href: '#que-detectamos' },
            { label: 'Planes', href: '#planes' },
          ].map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-muted-foreground hover:text-foreground transition-colors relative after:absolute after:bottom-0 after:left-0 after:h-px after:w-0 after:bg-primary after:transition-all hover:after:w-full"
            >
              {item.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link to="/login">Ingresar</Link>
          </Button>
          <Button asChild size="sm" className="shadow-lg shadow-primary/25 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80">
            <Link to="/register">
              Empezar gratis
              <ArrowRight className="ml-1.5 size-3.5" />
            </Link>
          </Button>
          <button
            className="md:hidden p-2 text-foreground"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Menu"
          >
            <div className="space-y-1.5">
              <div className={cn('w-5 h-px bg-foreground transition-all', mobileOpen && 'rotate-45 translate-y-[3.5px]')} />
              <div className={cn('w-5 h-px bg-foreground transition-all', mobileOpen && 'opacity-0')} />
              <div className={cn('w-5 h-px bg-foreground transition-all', mobileOpen && '-rotate-45 -translate-y-[3.5px]')} />
            </div>
          </button>
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden overflow-hidden border-b border-border/40 bg-background/95 backdrop-blur-xl"
          >
            <div className="px-6 py-4 space-y-3">
              {['Cómo funciona', 'Qué detectamos', 'Planes'].map((item) => (
                <a key={item} href="#" className="block text-muted-foreground hover:text-foreground py-2">
                  {item}
                </a>
              ))}
              <Button asChild className="w-full mt-2">
                <Link to="/register">Empezar gratis</Link>
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  )
}

/* ─────────────── hero ─────────────── */

function Hero() {
  const [headlineIdx, setHeadlineIdx] = useState(0)
  const headlines = ['Enterate de todo', 'Anticipate a todo', 'Ganale a todos']
  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)
  const bgX = useTransform(mouseX, [0, typeof window !== 'undefined' ? window.innerWidth : 1200], [-20, 20])
  const bgY = useTransform(mouseY, [0, typeof window !== 'undefined' ? window.innerHeight : 800], [-20, 20])

  useEffect(() => {
    const t = setInterval(() => setHeadlineIdx((i) => (i + 1) % headlines.length), 4000)
    return () => clearInterval(t)
  }, [headlines.length])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      mouseX.set(e.clientX)
      mouseY.set(e.clientY)
    }
    window.addEventListener('mousemove', onMove)
    return () => window.removeEventListener('mousemove', onMove)
  }, [mouseX, mouseY])

  return (
    <section className="relative min-h-screen flex items-center overflow-hidden pt-16">
      {/* fondo con gradiente animado y noise */}
      <div className="absolute inset-0 bg-[#080810]" />
      <motion.div
        style={{ x: bgX, y: bgY }}
        className="absolute inset-0"
      >
        <div className="absolute top-0 left-1/4 w-[800px] h-[800px] bg-primary/8 rounded-full blur-[150px]" />
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-accent/6 rounded-full blur-[120px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[100px]" />
      </motion.div>
      <div className="absolute inset-0 bg-grid opacity-60" />
      <div className="absolute inset-0 bg-noise opacity-20" />

      {/* figuras flotantes decorativas */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{ y: [-20, 20, -20], rotate: [0, 5, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-[15%] right-[12%] size-3 rounded-full border border-primary/30"
        />
        <motion.div
          animate={{ y: [15, -25, 15], rotate: [0, -3, 0] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-[35%] left-[8%] size-2 bg-accent/30 rounded-full"
        />
        <motion.div
          animate={{ y: [-10, 30, -10], x: [0, 5, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute bottom-[25%] right-[20%] size-4 border border-accent/15 rounded rotate-45"
        />
        <motion.div
          animate={{ y: [10, -15, 10] }}
          transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-[55%] left-[18%] text-[10px] font-mono text-primary/15 select-none"
        >
          24/7
        </motion.div>
        <motion.div
          animate={{ y: [-5, 10, -5] }}
          transition={{ duration: 11, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-[20%] left-[30%] text-[10px] font-mono text-accent/15 select-none"
        >
          live
        </motion.div>
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-6 w-full">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* texto */}
          <div className="pt-12 lg:pt-0">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            >
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/15 mb-8 backdrop-blur-sm">
                <Activity className="size-3.5" />
                Inteligencia artificial aplicada a tu negocio
              </span>
            </motion.div>

            <AnimatePresence mode="wait">
              <motion.h1
                key={headlineIdx}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                className="font-serif text-5xl sm:text-6xl lg:text-7xl xl:text-[5.5rem] leading-[1.05] tracking-tight text-balance"
              >
                {headlines[headlineIdx]}
                <br />
                <span className="text-gradient">lo que hace tu competencia</span>
              </motion.h1>
            </AnimatePresence>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3, ease: 'easeOut' }}
              className="mt-6 text-lg text-muted-foreground max-w-lg leading-relaxed"
            >
              Monitoreamos automáticamente a tus competidores — precios, productos, stock y catálogos —
              y te generamos <span className="text-foreground font-medium">insights accionables en español</span> con IA.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.5, ease: 'easeOut' }}
              className="mt-8 flex flex-col sm:flex-row gap-3"
            >
              <Button asChild size="lg" className="h-12 px-8 text-base font-semibold shadow-xl shadow-primary/25 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80">
                <Link to="/register">
                  Empezar gratis
                  <ArrowRight className="ml-2 size-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="h-12 px-8 text-base border-border/50 hover:bg-muted/50">
                <a href="#como-funciona">
                  Ver cómo funciona
                </a>
              </Button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground"
            >
              <span className="flex items-center gap-1.5">
                <Check className="size-3.5 text-accent" /> Sin tarjeta
              </span>
              <span className="flex items-center gap-1.5">
                <Check className="size-3.5 text-accent" /> 14 días gratis
              </span>
              <span className="flex items-center gap-1.5">
                <Check className="size-3.5 text-accent" /> Cancelá cuando quieras
              </span>
            </motion.div>
          </div>

          {/* dashboard mockup */}
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: 'easeOut' }}
            className="hidden lg:block relative"
          >
            <div className="relative rounded-2xl border border-border/30 bg-card/20 backdrop-blur-md overflow-hidden shadow-2xl shadow-primary/5">
              <div className="flex items-center gap-1.5 px-4 h-9 border-b border-border/20 bg-card/30">
                <div className="size-2.5 rounded-full bg-red-500/70" />
                <div className="size-2.5 rounded-full bg-amber-500/70" />
                <div className="size-2.5 rounded-full bg-emerald-500/70" />
                <div className="ml-auto flex items-center gap-1.5">
                  <div className="size-1.5 rounded-full bg-accent animate-pulse" />
                  <span className="text-[10px] text-accent font-medium">En vivo</span>
                </div>
              </div>
              <div className="p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">Resumen de inteligencia</span>
                  <MousePointer2 className="size-3.5 text-muted-foreground/40" />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Competidores', value: '14', change: '+2', up: true },
                    { label: 'Cambios hoy', value: '23', change: '+8', up: true },
                    { label: 'Alertas', value: '5', change: '-1', up: false },
                  ].map((stat) => (
                    <div key={stat.label} className="rounded-xl bg-muted/30 p-3 border border-border/10 hover:border-primary/20 transition-colors">
                      <div className="text-[10px] text-muted-foreground mb-1">{stat.label}</div>
                      <div className="text-xl font-bold tracking-tight">{stat.value}</div>
                      <div className={cn('text-[10px] font-semibold', stat.up ? 'text-emerald-400' : 'text-red-400')}>
                        {stat.change}
                      </div>
                    </div>
                  ))}
                </div>

                {/* mini chart */}
                <div className="rounded-xl bg-muted/20 p-3 border border-border/10">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] text-muted-foreground font-medium">Cambios detectados</span>
                    <span className="text-[10px] text-accent font-semibold">+34% esta semana</span>
                  </div>
                  <div className="flex items-end gap-1 h-12">
                    {[35, 55, 40, 70, 45, 80, 65, 90, 60, 95, 75, 100].map((h, i) => (
                      <AnimatedBar key={i} height={`${h}%`} delay={0.8 + i * 0.05} />
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  {[
                    { name: 'Distribuidora del Centro', change: '-12% precios', type: 'alerta' },
                    { name: 'Distribuidora Norte', change: 'Nuevo catálogo', type: 'novedad' },
                    { name: 'Hermanos López SRL', change: 'Stock crítico', type: 'oportunidad' },
                  ].map((item, i) => (
                    <motion.div
                      key={item.name}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1.2 + i * 0.15 }}
                      className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-muted/15 border border-border/10 hover:bg-muted/30 hover:border-primary/15 transition-all cursor-pointer group"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={cn(
                          'size-2 rounded-full ring-2 ring-offset-1 ring-offset-[#080810]',
                          item.type === 'alerta' ? 'bg-red-400 ring-red-400/30' :
                          item.type === 'novedad' ? 'bg-primary ring-primary/30' : 'bg-accent ring-accent/30',
                        )} />
                        <span className="text-sm">{item.name}</span>
                      </div>
                      <span className={cn(
                        'text-[10px] font-semibold px-2 py-0.5 rounded-full border',
                        tickerTypeStyles[item.type],
                      )}>
                        {item.change}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>

            <div className="absolute -bottom-3 -right-3 size-full rounded-2xl border border-primary/5 -z-10" />
            <div className="absolute -bottom-6 -right-6 size-full rounded-2xl border border-accent/5 -z-20" />
          </motion.div>
        </div>
      </div>

      {/* scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <span className="text-[10px] text-muted-foreground uppercase tracking-[0.2em]">Scroll</span>
        <div className="w-5 h-8 rounded-full border border-muted-foreground/30 flex items-start justify-center pt-1.5">
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            className="w-1 h-1.5 rounded-full bg-muted-foreground/60"
          />
        </div>
      </motion.div>
    </section>
  )
}

/* ─────────────── ticker ─────────────── */

function LiveTicker() {
  return (
    <div className="relative overflow-hidden border-y border-border/30 bg-card/30 backdrop-blur-sm py-3">
      <div className="absolute left-0 inset-y-0 w-20 bg-gradient-to-r from-background to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 inset-y-0 w-20 bg-gradient-to-l from-background to-transparent z-10 pointer-events-none" />
      <div className="flex animate-ticker gap-16 whitespace-nowrap">
        {[...tickerItems, ...tickerItems].map((item, i) => (
          <span key={i} className="inline-flex items-center gap-2 text-sm">
            <span className={cn(
              'inline-block size-1.5 rounded-full',
              item.type === 'alerta' ? 'bg-red-400' :
              item.type === 'novedad' ? 'bg-primary' : item.type === 'oportunidad' ? 'bg-accent' : 'bg-blue-400',
            )} />
            {item.label}
            <span className={cn(
              'text-[10px] font-semibold px-1.5 py-0.5 rounded border',
              tickerTypeStyles[item.type],
            )}>
              {item.type}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}

/* ─────────────── stats ─────────────── */

function StatItem({ label, end }: { label: string; end: number }) {
  const { ref, val, inView } = useCountUp(end, 2.5)
  return (
    <div className="text-center group">
      <span
        ref={ref}
        className="block font-serif text-4xl sm:text-5xl text-gradient tabular-nums"
      >
        {inView ? val.toLocaleString() : '0'}
      </span>
      <span className="text-sm text-muted-foreground mt-1 block group-hover:text-foreground transition-colors">{label}</span>
    </div>
  )
}

function Stats() {
  const stats = [
    { label: 'Competidores monitoreados', end: 1240 },
    { label: 'Cambios detectados por día', end: 3800 },
    { label: 'Distribuidoras activas', end: 340 },
    { label: 'Insights generados', end: 15200 },
  ]

  return (
    <section className="py-20 border-b border-border/30">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {stats.map((stat) => (
            <StatItem key={stat.label} label={stat.label} end={stat.end} />
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─────────────── problema / solución ─────────────── */

function ProblemSolution() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section id="como-funciona" ref={ref} className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, ease: 'easeOut' }}
          >
            <span className="text-xs font-semibold text-accent uppercase tracking-[0.2em]">El problema</span>
            <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl mt-4 leading-tight text-balance">
              ¿Todavía estás revisando competidores a mano?
            </h2>
            <div className="mt-6 space-y-4 text-muted-foreground">
              <p className="leading-relaxed">
                Abrir 20 pestañas, revisar precios uno por uno, hacer capturas de pantalla,
                pegar en Excel… perdés horas y siempre llega tarde.
              </p>
              <p className="leading-relaxed">
                Cuando te enteraste de que bajaron precios, ya perdiste 3 días de ventas.
              </p>
            </div>

            <motion.div
              initial={{ width: 0 }}
              animate={inView ? { width: '100%' } : {}}
              transition={{ duration: 1, delay: 0.3 }}
              className="h-px bg-gradient-to-r from-primary/50 via-accent/30 to-transparent mt-8"
            />

            <div className="mt-8">
              <span className="text-xs font-semibold text-accent uppercase tracking-[0.2em]">La solución</span>
              <h3 className="font-serif text-2xl sm:text-3xl mt-3 leading-tight text-balance">
                Nosotros monitoreamos todo. <span className="text-gradient">24/7.</span>
              </h3>
              <p className="mt-3 text-muted-foreground leading-relaxed">
                Conectá las fuentes que quieras — web, MercadoLibre, catálogos PDF — y nosotros
                detectamos cada cambio, lo analizamos con IA, y te decimos qué hacer.
              </p>
            </div>

            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              {[
                { label: 'Web y landing pages', icon: Globe },
                { label: 'MercadoLibre', icon: Search },
                { label: 'Catálogos PDF', icon: FileText },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl bg-muted/30 border border-border/30 hover:border-primary/30 transition-colors group cursor-default">
                  <item.icon className="size-3.5 text-primary group-hover:text-accent transition-colors" />
                  {item.label}
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2, ease: 'easeOut' }}
            className="relative"
          >
            <div className="relative rounded-2xl border border-border/30 overflow-hidden bg-gradient-to-br from-card/40 to-card/10 backdrop-blur-sm">
              <div className="p-6 space-y-5">
                <div className="flex items-center gap-3 pb-4 border-b border-border/20">
                  <div className="size-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                    <Search className="size-5 text-red-400" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">Sin DiffiX</div>
                    <div className="text-xs text-muted-foreground">~8 horas / semana</div>
                  </div>
                </div>

                <div className="space-y-2.5">
                  {[
                    'Revisar precios en 15 sitios web',
                    'Copiar datos a Excel manualmente',
                    'Buscar novedades en Google',
                    'Estimar tendencias "a ojo"',
                  ].map((item, i) => (
                    <motion.div
                      key={item}
                      initial={{ opacity: 0, x: -10 }}
                      animate={inView ? { opacity: 1, x: 0 } : {}}
                      transition={{ delay: 0.5 + i * 0.1 }}
                      className="flex items-center gap-3 px-3 py-2 rounded-xl bg-red-500/5 border border-red-500/10"
                    >
                      <span className="size-1.5 rounded-full bg-red-400 shrink-0" />
                      <span className="text-sm text-muted-foreground">{item}</span>
                    </motion.div>
                  ))}
                </div>

                <div className="flex items-center gap-3 pt-4 border-t border-border/20">
                  <div className="size-10 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                    <Zap className="size-5 text-accent" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">Con DiffiX</div>
                    <div className="text-xs text-accent font-semibold">~5 minutos / día</div>
                  </div>
                </div>

                <div className="space-y-2.5">
                  {[
                    'Todo automatizado, sin esfuerzo',
                    'Alertas de cambios al instante',
                    'Insights con IA en español',
                    'Dashboard actualizado en vivo',
                  ].map((item, i) => (
                    <motion.div
                      key={item}
                      initial={{ opacity: 0, x: -10 }}
                      animate={inView ? { opacity: 1, x: 0 } : {}}
                      transition={{ delay: 0.9 + i * 0.1 }}
                      className="flex items-center gap-3 px-3 py-2 rounded-xl bg-primary/5 border border-primary/10"
                    >
                      <Check className="size-3.5 text-accent shrink-0" />
                      <span className="text-sm">{item}</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>

            {/* decoración de fondo */}
            <div className="absolute -z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-accent/5 rounded-full blur-[80px]" />
          </motion.div>
        </div>
      </div>
    </section>
  )
}

/* ─────────────── cómo funciona ─────────────── */

const steps = [
  {
    icon: Globe,
    title: 'Conectá tus fuentes',
    desc: 'Agregá URLs de competidores, tiendas de MercadoLibre, o subí catálogos PDF. El sistema empieza a monitorear automáticamente.',
  },
  {
    icon: Bot,
    title: 'Analizamos con IA',
    desc: 'Cada cambio se compara con el estado anterior. La IA determina si es relevante y qué impacto tiene en tu negocio.',
  },
  {
    icon: Bell,
    title: 'Recibí insights',
    desc: 'Te llega un análisis claro con qué cambió, por qué importa y qué hacer — en español, sin tecnicismos.',
  },
]

function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <section id="que-detectamos" ref={ref} className="py-24 lg:py-32 border-y border-border/30 bg-gradient-to-b from-transparent via-muted/10 to-transparent">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-xs font-semibold text-accent uppercase tracking-[0.2em]">Cómo funciona</span>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl mt-4 leading-tight">
            Tres pasos. <span className="text-gradient">Cero esfuerzo.</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto">
            Configurás una vez y el sistema trabaja solo. Te avisamos solo cuando hay algo importante.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: i * 0.15 }}
              className="relative group"
            >
              <GlowCard className="p-8 h-full">
                <div className="size-12 rounded-xl bg-gradient-to-br from-primary/20 to-accent/10 flex items-center justify-center mb-5 group-hover:from-primary/30 group-hover:to-accent/20 transition-all">
                  <step.icon className="size-6 text-primary" />
                </div>
                <div className="text-5xl font-serif text-primary/10 absolute top-5 right-6 group-hover:text-primary/20 transition-colors">{String(i + 1).padStart(2, '0')}</div>
                <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
              </GlowCard>
              {i < steps.length - 1 && (
                <div className="hidden md:flex absolute top-1/2 -right-6 items-center">
                  <div className="w-8 h-px bg-gradient-to-r from-primary/30 to-transparent" />
                  <ArrowRight className="size-4 text-muted-foreground/30 -ml-px" />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─────────────── features ─────────────── */

const features = [
  {
    icon: TrendingUp,
    title: 'Precios actualizados al instante',
    desc: 'Detectamos subas, bajas y promociones de todos tus competidores en un solo lugar.',
  },
  {
    icon: Bell,
    title: 'Alertas inteligentes por urgencia',
    desc: 'Clasificamos cada cambio como alta, media o baja urgencia. Solo te alertamos cuando importa.',
  },
  {
    icon: FileText,
    title: 'Catálogos y PDFs digitalizados',
    desc: 'Subí cualquier catálogo PDF y lo analizamos automáticamente. Detectamos productos nuevos, bajas y cambios de precio.',
  },
  {
    icon: Bot,
    title: 'Insights con IA en español',
    desc: 'Cada cambio viene con un análisis claro: qué cambió, por qué importa, y qué deberías hacer.',
  },
  {
    icon: Shield,
    title: 'Monitoreo 24/7 sin labs',
    desc: 'El sistema revisa automáticamente todos los días a la madrugada. No necesitas acordarte de nada.',
  },
  {
    icon: BarChart3,
    title: 'Dashboard unificado',
    desc: 'Todo el panorama competitivo en un solo tablero. Filtrado por urgencia, fuente o competidor.',
  },
]

function Features() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <section ref={ref} className="py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-xs font-semibold text-accent uppercase tracking-[0.2em]">Qué detectamos</span>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl mt-4 leading-tight">
            Tu radar <span className="text-gradient">competitivo</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto">
            Todo lo que necesitás saber para tomar decisiones antes que los demás.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.08 }}
            >
              <GlowCard className="p-6 lg:p-8 h-full">
                <div className="size-10 rounded-lg bg-gradient-to-br from-primary/15 to-accent/5 flex items-center justify-center mb-4 group-hover:from-primary/25 group-hover:to-accent/10 transition-all">
                  <feature.icon className="size-5 text-primary" />
                </div>
                <h3 className="text-base font-semibold mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.desc}</p>
              </GlowCard>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─────────────── planes ─────────────── */

const plans = [
  {
    name: 'Free',
    price: '0',
    desc: 'Para probar el sistema',
    competitors: 2,
    features: ['2 competidores', 'Alertas por email', 'Dashboard básico', 'Actualización diaria'],
    cta: 'Empezar gratis',
    featured: false,
  },
  {
    name: 'Starter',
    price: '29',
    desc: 'Para distribuidoras en crecimiento',
    competitors: 5,
    features: ['5 competidores', 'Alertas email + dashboard', 'Insights con IA', 'Catálogos PDF', 'Actualización diaria'],
    cta: 'Empezar gratis',
    featured: true,
  },
  {
    name: 'Growth',
    price: '79',
    desc: 'Para equipos que quieren dominar',
    competitors: 10,
    features: ['10 competidores', 'Alertas en tiempo real', 'Insights IA avanzados', 'Catálogos PDF ilimitados', 'API de datos'],
    cta: 'Empezar gratis',
    featured: false,
  },
]

function Plans() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <section id="planes" ref={ref} className="py-24 lg:py-32 border-y border-border/30 bg-gradient-to-b from-transparent via-muted/10 to-transparent">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-xs font-semibold text-accent uppercase tracking-[0.2em]">Planes</span>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl mt-4 leading-tight">
            Arrancá gratis.{' '}
            <span className="text-gradient">Crece después.</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto">
            Sin tarjeta de crédito. 14 días gratis en cualquier plan.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6 lg:gap-8 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.12 }}
              className={cn(
                'relative rounded-2xl border p-8 transition-all duration-500',
                plan.featured
                  ? 'border-primary/40 bg-gradient-to-b from-card/60 to-card/30 shadow-xl shadow-primary/5 md:scale-105'
                  : 'border-border/30 bg-card/30 hover:border-border/50',
              )}
            >
              {plan.featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-primary to-accent text-primary-foreground text-[10px] font-bold uppercase tracking-widest shadow-lg shadow-primary/30">
                  Más popular
                </span>
              )}

              <div className="mb-6">
                <h3 className="text-lg font-semibold">{plan.name}</h3>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="font-serif text-4xl font-bold">${plan.price}</span>
                  <span className="text-sm text-muted-foreground">/mes</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">Hasta {plan.competitors} competidores</p>
                <p className="text-sm text-muted-foreground mt-3">{plan.desc}</p>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feat) => (
                  <li key={feat} className="flex items-start gap-2.5 text-sm">
                    <Check className="size-4 text-accent shrink-0 mt-0.5" />
                    {feat}
                  </li>
                ))}
              </ul>

              <Button
                asChild
                variant={plan.featured ? 'default' : 'outline'}
                className={cn('w-full', plan.featured ? 'shadow-lg shadow-primary/30 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80' : '')}
              >
                <Link to="/register">{plan.cta}</Link>
              </Button>
            </motion.div>
          ))}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ delay: 0.6 }}
          className="text-center text-sm text-muted-foreground mt-10"
        >
          ¿Más de 10 competidores?{' '}
          <a href="#" className="text-primary hover:underline">Contactanos para un plan Business</a>
        </motion.p>
      </div>
    </section>
  )
}

/* ─────────────── CTA final ─────────────── */

function FinalCTA() {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true })

  return (
    <section ref={ref} className="py-24 lg:py-32 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/3 to-transparent pointer-events-none" />
      <div className="mx-auto max-w-4xl px-6 text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.6 }}
        >
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20 mb-6">
            <Sparkles className="size-3.5" />
            Empezá hoy
          </span>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl leading-tight text-balance">
            Dejá de revisar competidores a mano.
          </h2>
          <p className="mt-4 text-lg text-muted-foreground max-w-lg mx-auto">
            En 5 minutos tenés todo configurado. Empezá gratis, sin compromiso.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <Button asChild size="lg" className="h-12 px-8 text-base font-semibold shadow-xl shadow-primary/25 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary/80">
              <Link to="/register">
                Empezar gratis
                <ArrowRight className="ml-2 size-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="h-12 px-8 text-base">
              <a href="#como-funciona">Ver cómo funciona</a>
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-4">Sin tarjeta · 14 días gratis · Cancelá cuando quieras</p>
        </motion.div>
      </div>
    </section>
  )
}

/* ─────────────── footer ─────────────── */

function Footer() {
  return (
    <footer className="border-t border-border/30 py-12">
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-lg bg-gradient-to-br from-primary to-accent/80 flex items-center justify-center">
              <BarChart3 className="size-4 text-primary-foreground" />
            </div>
            <span className="font-serif text-base">
              Diffi<span className="text-primary">X</span>
            </span>
          </div>
          <div className="flex items-center gap-6 text-xs text-muted-foreground">
            <span>Inteligencia competitiva automática para distribuidoras</span>
            <span className="hidden sm:inline">·</span>
            <span>&copy; {new Date().getFullYear()} DiffiX</span>
          </div>
        </div>
      </div>
    </footer>
  )
}

/* ─────────────── landing page ─────────────── */

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Nav />
      <Hero />
      <LiveTicker />
      <Stats />
      <ProblemSolution />
      <HowItWorks />
      <Features />
      <Plans />
      <FinalCTA />
      <Footer />
    </div>
  )
}