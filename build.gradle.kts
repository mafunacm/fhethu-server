import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    application
    kotlin("jvm") version "1.9.10"
}

group = "dev.fhehu"
version = "0.1.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation("io.ktor:ktor-server-core-jvm:2.3.4")
    implementation("io.ktor:ktor-server-netty-jvm:2.3.4")
    implementation("io.ktor:ktor-server-content-negotiation-jvm:2.3.4")
    implementation("io.ktor:ktor-serialization-kotlinx-json-jvm:2.3.4")
    implementation("ch.qos.logback:logback-classic:1.4.8")

    testImplementation("io.ktor:ktor-server-tests-jvm:2.3.4")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.10")
}

application {
    mainClass.set("dev.fhehu.ApplicationKt")
}

tasks.withType<KotlinCompile> {
    kotlinOptions.jvmTarget = "17"
}
