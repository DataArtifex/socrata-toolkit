using System;
using System.Linq;

// Install the package from Nuget first:
// PM> Install-Package CSM.SodaDotNet
using SODA;

var client = new SodaClient("https://data.sfgov.org", "YOURAPPTOKENHERE");

// Get a reference to the resource itself
// The result (a Resource object) is a generic type
// The type parameter represents the underlying rows of the resource
// and can be any JSON-serializable class
var dataset = client.GetResource("vw6y-z8j6");

// Resource objects read their own data
var rows = dataset.GetRows(limit: 5000);

Console.WriteLine("Got {0} results. Dumping first results:", rows.Count());

foreach (var keyValue in rows.First())
{
    Console.WriteLine(keyValue);
}            