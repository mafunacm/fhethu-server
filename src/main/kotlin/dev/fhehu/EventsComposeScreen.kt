package dev.fhehu

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.stickyHeader
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgeDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.smallTopAppBarColors
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberTopAppBarState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

private val supportedCategories = listOf("All", "Party", "Music", "Sports", "Comedy", "Expo")
private val inputDateFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.getDefault())
private val outputDateFormatter = DateTimeFormatter.ofPattern("EEE, d MMM", Locale.getDefault())

data class EventItem(
    val title: String,
    val category: String,
    val date: String,
    val time: String,
    val location: String,
    val address: String,
    val price: String,
    val source: String
)

@Composable
fun EventsScreen(
    events: List<EventItem>,
    onEventSelected: (EventItem) -> Unit = {}
) {
    var selectedCategory by rememberSaveable { mutableStateOf("All") }
    val today = LocalDate.now()

    val filteredEvents = remember(events, selectedCategory) {
        events
            .filter { selectedCategory == "All" || it.category == selectedCategory }
            .sortedWith(compareBy({ LocalDate.parse(it.date, inputDateFormatter) }, { it.time }))
    }

    val groupedEvents = remember(filteredEvents) {
        filteredEvents
            .groupBy { it.category }
            .toSortedMap(compareBy { supportedCategories.indexOf(it).takeIf { index -> index >= 0 } ?: supportedCategories.size })
    }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(modifier = Modifier.fillMaxSize()) {
            TopAppBar(
                title = { Text("SA Event Explorer") },
                colors = smallTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            )

            CategoryFilterRow(
                categories = supportedCategories,
                selectedCategory = selectedCategory,
                onCategorySelected = { selectedCategory = it }
            )

            if (filteredEvents.isEmpty()) {
                EmptyEventState()
                return@Surface
            }

            LazyColumn(
                state = rememberLazyListState(),
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp)
            ) {
                groupedEvents.forEach { (category, eventsInCategory) ->
                    stickyHeader {
                        CategoryHeader(category = category)
                    }
                    items(eventsInCategory) { event ->
                        EventCard(
                            event = event,
                            isToday = runCatching { LocalDate.parse(event.date, inputDateFormatter) == today }.getOrDefault(false),
                            onClick = { onEventSelected(event) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun CategoryFilterRow(
    categories: List<String>,
    selectedCategory: String,
    onCategorySelected: (String) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 12.dp, horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        categories.forEach { category ->
            FilterChip(
                selected = selectedCategory == category,
                onClick = { onCategorySelected(category) },
                label = { Text(category) },
                modifier = Modifier.defaultMinSize(minHeight = 40.dp)
            )
        }
    }
}

@Composable
private fun CategoryHeader(category: String) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(vertical = 12.dp, horizontal = 8.dp)
    ) {
        Text(
            text = category,
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun EventCard(
    event: EventItem,
    isToday: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = event.title,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.weight(1f),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                if (isToday) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Badge(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary
n                    ) {
                        Text(text = "Today", fontSize = 12.sp)
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = formatDateTime(event.date, event.time),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = "${event.location} – ${event.address}",
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(modifier = Modifier.height(6.dp))

            if (event.price.isNotBlank()) {
                Text(
                    text = "Price: ${event.price}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(6.dp))
            }

            Text(
                text = "Source: ${event.source}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun EmptyEventState() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp)
            .wrapContentHeight(Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "No events found",
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
            modifier = Modifier.padding(bottom = 8.dp)
        )
        Text(
            text = "Try another category or add more events to your feed.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center
        )
    }
}

private fun formatDateTime(date: String, time: String): String {
    return try {
        val localDate = LocalDate.parse(date, inputDateFormatter)
        localDate.format(outputDateFormatter) + " • " + time
    } catch (error: Exception) {
        "$date • $time"
    }
}

@Composable
fun EventDetailScreen(event: EventItem) {
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(modifier = Modifier.padding(24.dp)) {
            Text(
                text = event.title,
                style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold)
            )
            Spacer(modifier = Modifier.height(12.dp))
            Text(text = "Category: ${event.category}")
            Text(text = "Date: ${formatDateTime(event.date, event.time)}")
            Text(text = "Location: ${event.location}")
            Text(text = "Address: ${event.address}")
            Text(text = "Price: ${event.price}")
            Text(text = "Source: ${event.source}")
        }
    }
}

@Preview(showBackground = true)
@Composable
fun EventsScreenPreview() {
    val sampleEvents = listOf(
        EventItem(
            title = "Soweto Sound Festival",
            category = "Music",
            date = LocalDate.now().toString(),
            time = "18:00",
            location = "Soweto",
            address = "Zone 6 – Eyethu Lifestyle Centre",
            price = "R120",
            source = "Quicket"
        ),
        EventItem(
            title = "Comedy Open Mic",
            category = "Comedy",
            date = LocalDate.now().plusDays(1).toString(),
            time = "20:30",
            location = "Johannesburg",
            address = "Braamfontein – The Laugh Lounge",
            price = "R80",
            source = "Ticketpro"
        ),
        EventItem(
            title = "City Expo 2026",
            category = "Expo",
            date = LocalDate.now().plusDays(3).toString(),
            time = "10:00",
            location = "Cape Town",
            address = "CTICC – Hall 2",
            price = "R250",
            source = "Webtickets"
        ),
        EventItem(
            title = "Victory Soccer Derby",
            category = "Sports",
            date = LocalDate.now().plusDays(2).toString(),
            time = "15:00",
            location = "Pretoria",
            address = "Loftus Versfeld Stadium",
            price = "R320",
            source = "SuperSport Tickets"
        ),
        EventItem(
            title = "Rooftop Party After Dark",
            category = "Party",
            date = LocalDate.now().plusDays(4).toString(),
            time = "22:00",
            location = "Durban",
            address = "Pier 10 Rooftop",
            price = "Free entry",
            source = "Plankton"
        )
    )

    EventsScreen(events = sampleEvents)
}
