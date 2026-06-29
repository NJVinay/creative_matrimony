export default function TermsOfService() {
    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl text-foreground">
            <h1 className="text-3xl font-bold mb-6">Terms of Service</h1>
            <p className="mb-4">Effective Date: {new Date().toLocaleDateString()}</p>

            <section className="space-y-4">
                <h2 className="text-xl font-bold">1. Acceptance of Terms</h2>
                <p>By accessing or using our services, you agree to be bound by these Terms.</p>

                <h2 className="text-xl font-bold">2. Eligibility</h2>
                <p>You must be at least 18 years old to use our services.</p>

                <h2 className="text-xl font-bold">3. User Conduct</h2>
                <p>You agree not to misuse our services or violate any laws.</p>

                <h2 className="text-xl font-bold">4. Termination</h2>
                <p>We reserve the right to terminate or suspend your account at any time.</p>
            </section>
        </div>
    );
}
