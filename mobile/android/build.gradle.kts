allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}

// Stripe's Android plugin declares the private Tap and Pay SDK as a runtime
// dependency of an optional issuing push-provisioning library. The app uses
// Stripe PaymentSheet only, and release lint must not resolve that SDK.
subprojects {
    if (name == "stripe_android") {
        dependencies.components.withModule(
            "com.stripe:stripe-android-issuing-push-provisioning"
        ) {
            allVariants {
                withDependencies {
                    removeAll {
                        it.group == "com.google.android.gms" &&
                            it.name == "play-services-tapandpay"
                    }
                }
            }
        }
    }
}

subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
