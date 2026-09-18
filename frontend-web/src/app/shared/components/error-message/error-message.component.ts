import { Component, Input } from '@angular/core';
@Component({selector: 'app-error-message', standalone: true, template: '<div class="state-panel state-error" role="alert"><p>{{ message }}</p></div>'})
export class ErrorMessageComponent { @Input() message = 'No fue posible cargar la información.'; }
