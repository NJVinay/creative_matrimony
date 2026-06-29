export default function PrivacyPolicy() {
    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl text-foreground">
            <h1 className="text-3xl font-bold mb-6">Privacy Policy</h1>
            <p className="mb-4">Effective Date: {new Date().toLocaleDateString()}</p>

            <section className="space-y-4">
                <h2 className="text-xl font-bold">1. Information We Collect</h2>
                <p>We collect information you provide directly to us, such as when you create an account, update your profile, or communicate with other users.</p>

                <h2 className="text-xl font-bold">2. How We Use Information</h2>
                <p>We use the information to provide, maintain, and improve our services, including matching you with potential partners.</p>

                <h2 className="text-xl font-bold">3. Data Security</h2>
                <p>We implement reasonable security measures to protect your personal information.</p>

                <h2 className="text-xl font-bold">4. Contact Us</h2>
                <p>If you have any questions, please contact us at support@creativematrimony.com.</p>
            </section>
        </div>
    );
}
