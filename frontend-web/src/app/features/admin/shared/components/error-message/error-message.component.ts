import { Component, Input } from '@angular/core';
@Component({ selector: 'app-error-message', standalone: true, template: '<p class="error">{{ message }}</p>', styles: ['.error{color:#b91c1c;padding:1rem;text-align:center}'] })
export class ErrorMessageComponent { @Input() message = 'No fue posible cargar la información.'; }
