import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../../../core/services/api.service';
import { AuthService } from '../../../auth/services/auth.service';
import { forkJoin } from 'rxjs';
import {
  ProductAvailabilityResponse,
  ProductoVariante,
  ProductVariantsResponse
} from '../../../../shared/models/producto.model';
import { AvailabilityListComponent } from '../../components/availability-list/availability-list.component';
import { VariantSelectorComponent } from '../../components/variant-selector/variant-selector.component';
import { CatalogService } from '../../services/catalog.service';
import { CartService } from '../../../cart/services/cart.service';
import { API_URL } from '../../../../core/config/api.config';
import { BackLinkComponent } from '../../../../shared/components/back-link.component';

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    VariantSelectorComponent,
    AvailabilityListComponent
    , BackLinkComponent
  ],
  templateUrl: './product-detail.component.html',
  styleUrl: './product-detail.component.scss'
})
export class ProductDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly catalogService = inject(CatalogService);
  private readonly cartService = inject(CartService);
  private readonly snackBar = inject(MatSnackBar);

  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  productId = 0;

  variants: ProductVariantsResponse | null = null;
  availability: ProductAvailabilityResponse | null = null;
  price = '';
  description = '';
  imageUrl = 'assets/catalog/editorial-menswear.png';
  isLoading = true;
  selectedVariant: ProductoVariante | null = null;
  isAddingToCart = false;

  ngOnInit(): void {
    const productId = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isInteger(productId) || productId <= 0) {
      this.handleError();
      return;
    }

    this.productId = productId;
    forkJoin({
      variants: this.catalogService.getProductVariants(productId),
      availability: this.catalogService.getProductAvailability(productId),
      products: this.catalogService.getProducts()
    }).subscribe({
      next: (response) => {
        this.variants = response.variants;
        this.availability = response.availability;
        const product = response.products.find((item) => item.id_producto === productId);
        this.price = product?.precio_base ?? '';
        this.description = product?.descripcion ?? '';
        this.imageUrl = this.resolveImageUrl(product?.imagen_url);
        this.isLoading = false;
        this.recordPreference('vista');
      },
      error: () => this.handleError()
    });
  }

  selectVariant(variant: ProductoVariante | null): void {
    this.selectedVariant = variant;
    if (variant) this.recordPreference('seleccion');
  }

  recordPreference(tipo: 'vista' | 'seleccion' | 'favorita'): void {
    if (!this.auth.hasSession()) return;
    this.api.post('/api/experience/preferences', {tipo, id_producto: this.productId,
      id_variante: tipo === 'seleccion' ? this.selectedVariant?.id_variante : null}).subscribe({
      next: () => {if (tipo === 'favorita') this.snackBar.open('Categoría guardada como favorita', 'Cerrar', {duration: 3000});},
      error: () => {if (tipo === 'favorita') this.snackBar.open('No se pudo guardar la preferencia', 'Cerrar', {duration: 3000});}
    });
  }

  hasSession(): boolean { return this.auth.hasSession(); }

  addToCart(): void {
    if (this.selectedVariant === null) {
      this.snackBar.open('Selecciona una talla y un color disponibles', 'Cerrar', { duration: 4000 });
      return;
    }

    if (!this.hasSession()) {
      this.snackBar.open('Inicia sesión como cliente para agregar productos al carrito', 'Iniciar sesión', { duration: 5000 })
        .onAction()
        .subscribe(() => {
          void this.router.navigate(['/login']);
        });
      return;
    }

    this.isAddingToCart = true;
    this.cartService.addItem(this.selectedVariant.id_variante, 1).subscribe({
      next: () => {
        this.isAddingToCart = false;
        this.snackBar.open('Producto agregado al carrito', 'Cerrar', { duration: 3000 });
      },
      error: (error: { status?: number; error?: { message?: string; detail?: string } }) => {
        this.isAddingToCart = false;
        if (error.status === 401) {
          this.snackBar.open('Sesión expirada. Por favor, inicia sesión nuevamente', 'Iniciar sesión', { duration: 5000 })
            .onAction()
            .subscribe(() => {
              void this.router.navigate(['/login']);
            });
          return;
        }
        if (error.status === 403) {
          this.snackBar.open('Debes iniciar sesión con una cuenta de Cliente para usar el carrito', 'Cerrar', { duration: 5000 });
          return;
        }
        const errorMsg = error.error?.detail ?? error.error?.message ?? 'No fue posible agregar el producto';
        this.snackBar.open(errorMsg, 'Cerrar', { duration: 5000 });
      }
    });
  }

  private handleError(): void {
    this.isLoading = false;
    this.snackBar.open('No fue posible cargar el detalle del producto', 'Cerrar', { duration: 5000 });
  }

  reserveSelectedVariant(): void {
    if (!this.selectedVariant) {
      this.snackBar.open('Selecciona una talla y un color disponibles', 'Cerrar', { duration: 4000 });
      return;
    }
    if (!this.hasSession()) {
      this.snackBar.open('Inicia sesión para reservar esta prenda', 'Cerrar', { duration: 4000 });
      return;
    }
    void this.router.navigate(['/reservations'], { queryParams: {
      producto_id: this.productId,
      producto_nombre: this.variants?.nombre_producto ?? '',
      variante_id: this.selectedVariant.id_variante,
      talla: this.selectedVariant.talla,
      color: this.selectedVariant.color,
      imagen: this.imageUrl,
      precio: this.price
    }});
  }

  useFallbackImage(event: Event): void {
    const image = event.target as HTMLImageElement;
    image.onerror = null;
    image.src = 'assets/catalog/editorial-menswear.png';
  }

  private resolveImageUrl(imageUrl?: string | null): string {
    if (!imageUrl) return 'assets/catalog/editorial-menswear.png';
    return imageUrl.startsWith('http') ? imageUrl : `${API_URL}${imageUrl}`;
  }
}
