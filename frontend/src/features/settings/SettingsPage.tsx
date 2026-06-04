import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

export default function SettingsPage() {
  return (
    <div className="p-6 max-w-xl">
      <h1 className="text-2xl font-bold mb-6">Configuración</h1>

      <Card>
        <CardHeader>
          <CardTitle>Notificaciones y perfil</CardTitle>
          <CardDescription>
            Administrá tus preferencias de alertas y datos de cuenta.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground py-8 text-center">
            Próximamente — configuración de notificaciones y perfil.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
