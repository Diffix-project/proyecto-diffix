import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PLANES } from '@/types'

export default function BillingPage() {
  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Plan y facturación</h1>

      <div className="grid gap-4 sm:grid-cols-2">
        {PLANES.map((plan) => (
          <Card key={plan.id}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{plan.nombre}</CardTitle>
                {plan.id === 'free' && <Badge variant="secondary">Actual</Badge>}
              </div>
              <CardDescription>
                {plan.precio === 0 ? 'Gratis' : `$${plan.precio}/mes`}
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-1">
              <p>
                Competidores:{' '}
                <span className="font-medium text-foreground">
                  {plan.competidores === null ? 'Ilimitados' : plan.competidores}
                </span>
              </p>
              <p>Alertas: {plan.alertas}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="mt-6 text-sm text-muted-foreground text-center">
        Próximamente — integración con Mercado Pago para upgrade.
      </p>
    </div>
  )
}
