document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('#loginForm');
    const password = document.querySelector('#id_password');
    const passwordToggle = document.querySelector('#passwordToggle');
    const continueButton = document.querySelector('#continueButton');

    passwordToggle?.addEventListener('click', () => {
        const isVisible = password.type === 'text';
        password.type = isVisible ? 'password' : 'text';
        passwordToggle.textContent = isVisible ? 'Show' : 'Hide';
        passwordToggle.setAttribute('aria-pressed', String(!isVisible));
        password.focus({ preventScroll: true });
    });

    form?.addEventListener('submit', (event) => {
        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
            return;
        }

        continueButton.disabled = true;
        continueButton.classList.add('is-loading');
        continueButton.setAttribute('aria-busy', 'true');
        continueButton.querySelector('.button-label').textContent = 'Signing in';
    });
});
