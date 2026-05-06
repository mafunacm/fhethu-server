package dev.fhehu

import io.ktor.http.*
import io.ktor.server.testing.*
import kotlin.test.Test
import kotlin.test.assertEquals

class ApplicationTest {
    @Test
    fun testRootEndpoint() {
        testApplication {
            application { module() }

            client.get("/").apply {
                assertEquals(HttpStatusCode.OK, status)
                assertEquals("fhehu-server is running", bodyAsText())
            }
        }
    }
}
